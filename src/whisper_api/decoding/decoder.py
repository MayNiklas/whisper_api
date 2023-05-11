import datetime as dt
import gc
import logging
import signal
from multiprocessing.connection import Connection
from types import FrameType
from typing import Literal, Optional

import torch
import whisper

from whisper_api.data_models.data_types import model_sizes_str_t, task_type_str_t
from whisper_api.data_models.task import WhisperResult, Task
from whisper_api.environment import DEVELOP_MODE, LOAD_MODEL_ON_STARTUP, CPU_FALLBACK_MODEL

vram_model_map: dict[model_sizes_str_t, int] = {
    "large": 10,
    "medium": 5,
    "small": 2,
    "base": 1,
}

model_names = list(vram_model_map.keys())


class Decoder:

    @staticmethod
    def init_and_run(pipe_to_parent: Connection,
                     logger: logging.Logger,
                     unload_model_after_s: bool = True,
                     use_gpu_if_available: bool = True,
                     max_model_to_use: model_sizes_str_t = None):
        """
        Initialize the decoder and run it
        Args:
            pipe_to_parent: pipe to receive tasks from the parent process
            logger: logger to log with
            unload_model_after_s: if model should be kept in memory after loading
            use_gpu_if_available: if GPU should be used if available
            max_model_to_use: max model to use, may be None in GPU Mode

        Returns:

        """

        decoder = Decoder(pipe_to_parent,
                          logger,
                          unload_model_after_s,
                          use_gpu_if_available=use_gpu_if_available,
                          max_model_to_use=max_model_to_use)
        try:
            decoder.run()
        # stop process 'gracefully' when KeyboardInterrupt
        except KeyboardInterrupt:
            exit(0)

    def __init__(self,
                 pipe_to_parent: Connection,
                 logger: logging.Logger,
                 unload_model_after_s: bool = True,
                 use_gpu_if_available: bool = True,
                 max_model_to_use: model_sizes_str_t = None):
        """
        Holding and managing the whisper model
        Args:
            pipe_to_parent: pipe to receive tasks from the parent process
            logger: logger to log with
            unload_model_after_s: if model should be kept in memory after loading
            use_gpu_if_available: if GPU should be used if available
            max_model_to_use: max model to use, may be None in GPU Mode
        """

        self.pipe_to_parent = pipe_to_parent
        self.logger = logger

        # register signal handlers
        signal.signal(signal.SIGINT, self.clean_up_and_exit)   # Handle Control + C
        signal.signal(signal.SIGTERM, self.clean_up_and_exit)  # Handle .terminate() from parent process
        signal.signal(signal.SIGHUP, self.clean_up_and_exit)   # Handle terminal closure

        # determine mode to run in
        self.max_model_to_use = max_model_to_use
        self.use_gpu_if_available = use_gpu_if_available
        self.gpu_mode = self.__is_gpu_mode(use_gpu_if_available)
        if not self.gpu_mode and self.max_model_to_use is None:
            # take requested model and below in CPU mode
            self.max_model_to_use = CPU_FALLBACK_MODEL
            self.logger.warning(f"No explicit model for CPU was specified setting max-model to '{CPU_FALLBACK_MODEL=}'")

        self.unload_model_after_s = unload_model_after_s

        self.model: whisper.Whisper = None
        self.last_loaded_model_size: model_sizes_str_t = None
        if LOAD_MODEL_ON_STARTUP:
            self.model: whisper.Whisper = self.load_model(self.gpu_mode, self.max_model_to_use)

    def __is_gpu_mode(self, use_gpu_if_available: bool):
        """ Determine if GPU can and shall be used or not """
        if not torch.cuda.is_available():
            self.logger.warning("CUDA is not available, using CPU-mode")
            return False

        if not use_gpu_if_available:
            self.logger.warning("GPU mode is disabled, using CPU-mode (CUDA would be available...)")
            return False

        self.logger.info("Using GPU Mode")
        return True

    def run(self):
        """
        Read from task_queue, process tasks and send results to parent process
        Returns:

        """
        self.logger.info(f"Decoder is listening for messages")
        while True:
            # wait for tasks, if no task after time specified in UNLOAD_MODEL_AFTER_S, unload model
            # None means no timeout so model will never unload
            # TODO: if user sets 0 it will result in busy waiting
            #  maybe think of better solution than pinning the unload to the poll timeout
            if not self.pipe_to_parent.poll(self.unload_model_after_s):
                # can only trigger if timeout is set
                self.__unload_model()
                continue

            msg = self.pipe_to_parent.recv()

            task_name = msg.get("task_name", None)
            val = msg.get("data", None)

            if task_name is None:
                self.logger.debug(f"Decoder received '{task_name=}', weird... continuing - data: {msg=}")
                continue

            elif task_name == "exit":
                self.logger.warning("Decoder received exit, exiting process.")
                exit(0)

            # guarding against all messages that are not decode messages
            if task_name != "decode":
                self.logger.warning(f"Can't handle message: '{msg=}'")
                continue

            # the json must be a decode-task from here on
            # all other cases are caught above

            # reconstruct task from json
            try:
                task = Task.from_json(val)
            except Exception as e:
                self.logger.warning(f"Could not parse task from json (continuing): '{e}'")
                continue

            # update state and send to parent
            task.status = "processing"
            self.pipe_to_parent.send(task.to_json)

            # start processing
            whisper_result = self.__run_model(audio_path=task.audiofile_name,
                                              task=task.task_type,
                                              source_language=task.source_language,
                                              model_size=task.target_model_size)

            # set result and send to parent
            if whisper_result is not None:
                task.whisper_result = whisper_result
                task.status = "finished"
            else:
                task.status = "failed"

            self.pipe_to_parent.send(task.to_json)

    def __unload_model(self):
        """
        Unload the model from memory (as good as possible)
        """
        if self.model is None:
            self.logger.debug(f"Tried to unload model, but None is loaded")
            return

        self.logger.info(f"Unloading model '{self.last_loaded_model_size}'")
        self.model = None
        gc.collect()
        # clear CUDA cache as well when GPU mode
        if self.gpu_mode:
            torch.cuda.empty_cache()
        self.logger.debug(f"Model '{self.last_loaded_model_size}' unloaded")

    def clean_up_and_exit(self, signum: int, frame: Optional[FrameType]):
        """
        Clean up and exit the process
        """
        self.logger.warning(f"Exit was called {signum=}")
        self.__unload_model()
        exit(0)

    def __get_models_below(self, model_name: model_sizes_str_t) -> list[model_sizes_str_t]:
        """ includes the given model itself """
        return model_names[model_names.index(model_name):]

    def get_possible_model_names_for_gpu(self,
                                         sizes_to_try: Optional[list[model_sizes_str_t]] = None,
                                         max_vram=None
                                         ) -> Optional[list[model_sizes_str_t]]:
        """
        Get all models that would technically fit the GPU if all memory was available
        Args:
            sizes_to_try: a list of models to try out (default is all models)
            max_vram: max vram that the model should take (default is current_model_size + free vram)

        Returns: list of all possible models in descending size order

        """
        if DEVELOP_MODE:
            self.logger.warning(f"DEVELOPMENT MODE SET - RETURNING 'base' MODEL")
            return ["base"]

        if max_vram is None:
            # free VRAM space + current model size if exists
            mem_info = torch.cuda.mem_get_info()
            # there is no model in memory, just use free memory
            if self.model is None:
                max_vram = mem_info[0]
            # model size + free memory
            else:
                max_vram = mem_info[0] + vram_model_map.get(self.last_loaded_model_size)

            self.logger.debug(
                f"Calculated a total of {max_vram} memory to work with (free VRAM + potential loaded model)"
            )

        # use only subset of models if specified
        if sizes_to_try:
            models_to_try_dict = {size: vram_model_map[size] for size in sizes_to_try}
        else:
            models_to_try_dict = vram_model_map

        potential_models = []
        for model_name, model_size in models_to_try_dict.items():
            # sum free and allocated memory space to get the full VRAM capacity of GPU
            if max_vram >= model_size * 1e9:
                potential_models.append(model_name)

        return potential_models

    def __try_load(self, gpu_mode: bool, model_size: model_sizes_str_t) -> Optional[model_sizes_str_t]:
        """
        Try to load a given model, set self.model and self.last_loaded_model_size if successful
        Args:
            gpu_mode: whether to address the gpu on model load
            model_size: requested model size

        Returns: model name if success else None

        """
        self.logger.debug(f"Trying to load model {model_size}")
        try:
            if gpu_mode:
                self.model = whisper.load_model(name=model_size, in_memory=self.unload_model_after_s)
            else:
                self.model = whisper.load_model(name=model_size, in_memory=self.unload_model_after_s, device="cpu")

            self.last_loaded_model_size = model_size
            self.logger.info(f"Successfully loaded model '{model_size}'")
            return model_size

        except torch.cuda.OutOfMemoryError:
            self.logger.warning(f"Model '{model_size}' currently doesn't fit device.")
            return

    def load_model(self, gpu_mode: bool, requested_model_size: model_sizes_str_t = None) -> whisper.Whisper:
        """
        Load a model into memory.

        GPU Mode
            Trying to load given model, if it doesn't fit, try to load the next smaller model that fits
            If no model is given (None), the largest model that fits is loaded
            If no model fits GPU the system tries to load to CPU

        CPU Mode
            A model size must be specified, if the model doesn't fit, the largest (smaller) model that fits is loaded

        Args:
            gpu_mode: decide whether to load model on GPU or CPU
            requested_model_size: size of the model to load (optional in GPU mode, required in CPU mode)
                                  if model doesn't fit, all models below will be tried until one fits

        Returns:
            the loaded model, None if models does not fit on the mode's device

        Raises:
            MemoryError if no model can be loaded to either GPU or CPU

        """

        # get all potentially fitting models
        if gpu_mode:
            # auto-detect possible models
            self.logger.debug(f"CUDA is available, trying to work on GPU.")
            # detect all models that fit gpu
            if requested_model_size is None:
                possible_sizes = self.get_possible_model_names_for_gpu()

            # detect all models that fit GPU and are required model or below
            else:
                models_to_try = self.__get_models_below(requested_model_size)
                possible_sizes = self.get_possible_model_names_for_gpu(models_to_try)

            # if no model fits switch back to cpu mode
            if len(possible_sizes) < 1:
                self.logger.warning(f"No model fits on GPU, falling back to CPU-mode.")
                gpu_mode = False

        if not gpu_mode:
            # take requested model and below in CPU mode
            if requested_model_size is None:
                # CPU mode must have an explicit max-model-size
                requested_model_size = self.max_model_to_use
                self.logger.info(f"No explicit model for CPU was specified trying '{self.max_model_to_use}' and below")

            possible_sizes = self.__get_models_below(requested_model_size)

        # check if correct model is already loaded
        if self.model is not None:
            # there are mainly two cases to be able to determine which case happened for logging
            # model is the requested one (and not None - prevents hiccups on first run)
            if requested_model_size == self.last_loaded_model_size and requested_model_size is not None:
                self.logger.debug(f"Target model '{requested_model_size}' already loaded")
                return self.model

            # TODO maybe prevent this case from happening again and again if max only fits in ideal circumstances
            # loaded model is the largest possible model
            elif self.last_loaded_model_size == possible_sizes[0]:
                self.logger.debug(f"Target model '{possible_sizes[0]}' already loaded")
                return self.model

            # we've got a not wanted model in our memory - purge it
            self.logger.debug(f"Got not wanted model in memory ('{self.last_loaded_model_size}'), unloading it...")
            self.__unload_model()

        # try to load the model asked for if given
        if requested_model_size is not None:
            self.logger.debug(f"Trying to load requested model size '{requested_model_size}'")

            # try to load model, if model is loaded return the set self.model
            if self.__try_load(gpu_mode, requested_model_size) is not None:
                return self.model

            self.logger.warning(f"Requested model '{requested_model_size}' doesn't fit.")

        self.logger.debug(
            f"No model loaded. Trying to find the largest model that's currently possible. {possible_sizes=}")
        self.logger.debug(f"Current model state: {self.last_loaded_model_size=}, {self.model=}")

        # iterate over all possible models, try to find the largest one that currently fits
        for model_size in possible_sizes:
            model_size = self.__try_load(gpu_mode, model_size)
            if model_size is not None:
                break

        # okay not model could be loaded. raise. but now we just need to determine the exception's description
        else:
            if gpu_mode:
                raise MemoryError(
                    "No model currently fits the GPU. Set 'USE_GPU_IF_AVAILABLE' to 0 to disable GPU mode."
                )
            else:
                info = ("CUDA is available, but disabled by 'USE_GPU_IF_AVAILABLE'."
                        if torch.cuda.is_available() else "CUDA is not available.")

                raise MemoryError(f"No model currently fits the CPU. {info}")

        # we made it - wuhu!
        self.logger.info(f"Model '{model_size}' loaded successfully!")

        return self.model

    def __run_model(self, audio_path: str, task: task_type_str_t,
                    source_language: Optional[str],
                    model_size: model_sizes_str_t = None) -> Optional[WhisperResult]:
        """
        'Generic' function to run the model and centralize the needed logic
        This is used by transcribe() and translate()
        For args see transcribe() and translate()
        Args:
            model_size: overwrites the decoder-wide set max_model_size

        Returns:
            the result of the whisper models transcription/translation and the transcription time in seconds
        """

        # load model
        model = self.load_model(self.gpu_mode, model_size or self.max_model_to_use)  # model can still be None

        # load failed, load model should try everything to load one, so it's a lost cause
        if model is None:
            self.logger.warning("Could not load any model, aborting task.")
            return None

        self.logger.info(f"Start decode of '{audio_path}' with model '{self.last_loaded_model_size}', {task=}")

        # start decoding
        start = dt.datetime.now()
        result = model.transcribe(audio_path, language=source_language, task=task)
        end = dt.datetime.now()

        self.logger.info(f"Finished decode of '{audio_path}' with model '{self.last_loaded_model_size}', {task=}")

        return WhisperResult(**result,
                             start_time=start,
                             end_time=end,
                             used_model_size=self.last_loaded_model_size,
                             # TODO is this the correct code for translation?
                             output_language="en_US" if task == "translate" else result["language"],
                             used_device="gpu" if self.gpu_mode else "cpu"
                             )

    def transcribe(self, audio_path: str,
                   source_language: Optional[str],
                   model_size: model_sizes_str_t = None) -> Optional[WhisperResult]:
        """
        Transcribe an audio file in its source language
        Args:
            audio_path: path to the audio file
            source_language: language of the audio file
            model_size: target model size, if None the largest model that fits the GPU is used

        Returns:
                the result of the whisper models transcription
        """
        # transcribe the file
        transcription_result = self.__run_model(audio_path, "transcribe", source_language, model_size)

        return transcription_result

    def translate(self, audio_path: str,
                  source_language: Optional[str],
                  model_size: model_sizes_str_t = None) -> Optional[WhisperResult]:
        """
        Translate a given audio file to english
        Args:
            audio_path: path to the audio file
            source_language: language of the audio file
            model_size: target model size, if None the largest model that fits the GPU is used

        Returns:
                the result of the whisper models translation (to english)
        """
        # translate the file
        translation_result = self.__run_model(audio_path, "translate", source_language, model_size)

        return translation_result
