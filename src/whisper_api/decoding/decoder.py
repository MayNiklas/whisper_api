import datetime as dt
import gc
import signal
from multiprocessing.connection import Connection
from types import FrameType
from typing import Literal, Optional

import torch
import whisper

from whisper_api.data_models.data_types import model_sizes_str_t, task_type_str_t
from whisper_api.data_models.task import WhisperResult, Task
from whisper_api.environment import DEVELOP_MODE, LOAD_MODEL_ON_STARTUP

vram_model_map: dict[model_sizes_str_t, int] = {
    "large": 10,
    "medium": 5,
    "small": 2,
    "base": 1,
}


class Decoder:

    @staticmethod
    def init_and_run(pipe_to_parent: Connection, unload_model_after_s: bool = True):
        """
        Initialize the decoder and run it
        Args:
            pipe_to_parent: pipe to receive tasks from the parent process
            unload_model_after_s: if model should be kept in memory after loading

        Returns:

        """

        decoder = Decoder(pipe_to_parent, unload_model_after_s)
        try:
            decoder.run()
        # stop process 'gracefully' when KeyboardInterrupt
        except KeyboardInterrupt:
            exit(0)

    def __init__(self, pipe_to_parent: Connection, unload_model_after_s: bool = True):
        """
        Holding and managing the whisper model
        Args:
            pipe_to_parent: pipe to receive tasks from the parent process
            unload_model_after_s: if model should be kept in memory after loading
        """
        if not torch.cuda.is_available():
            raise NotImplementedError("CPU decoding is not implemented yet")

        self.pipe_to_parent = pipe_to_parent

        # register signal handlers
        signal.signal(signal.SIGINT, self.clean_up_and_exit)   # Handle Control + C
        signal.signal(signal.SIGTERM, self.clean_up_and_exit)  # Handle .terminate() from parent process
        signal.signal(signal.SIGHUP, self.clean_up_and_exit)   # Handle terminal closure

        self.unload_model_after_s = unload_model_after_s

        self.gpu_vram = torch.cuda.mem_get_info()[0]

        self.model: whisper.Whisper = None
        self.last_loaded_model_size: model_sizes_str_t = None
        if LOAD_MODEL_ON_STARTUP:
            self.model: whisper.Whisper = self.load_model()

    def run(self):
        """
        Read from task_queue, process tasks and send results to parent process
        Returns:

        """
        print(f"Decoder is listening for messages")
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

            print(f"Got message: {msg}")

            task_name = msg.get("task_name", None)
            val = msg.get("data", None)

            if task_name is None:
                print(f"Decoder received {msg=}, weird... continuing")
                continue

            elif task_name == "exit":
                print("Decoder received exit, exiting process.")
                exit(0)

            # guarding against all messages that are not decode messages
            if task_name != "decode":
                print(f"Can't handle message: '{msg=}'")
                continue

            # the json must be a decode-task from here on
            # all other cases are caught above

            # reconstruct task from json
            try:
                task = Task.from_json(val)
            except Exception as e:
                print(f"Could not parse task from json (continuing): '{e}'")
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
            print(f"Tried to unload model, but None is loaded")
            return

        print(f"Unloading model '{self.last_loaded_model_size}'")
        self.model = None
        gc.collect()
        torch.cuda.empty_cache()
        print(f"Model '{self.last_loaded_model_size}' unloaded")

    def clean_up_and_exit(self, signum: int, frame: Optional[FrameType]):
        """
        Clean up and exit the process
        """
        print(f"Exit was called {signum=}")
        self.__unload_model()
        exit(0)

    def get_possible_model_names_for_gpu(self) -> Optional[list[model_sizes_str_t]]:
        """
        Get the largest model that fits on the GPU
        Returns: list of all possible models in descending size order

        """
        if DEVELOP_MODE:
            print(f"DEVELOPMENT MODE SET - RETURNING 'base' MODEL")
            return ["base"]

        potential_models = []
        for model_name, model_size in vram_model_map.items():
            if self.gpu_vram >= model_size * 1e9:
                # print(f"Potential model: '{model_name}'")
                potential_models.append(model_name)

        return potential_models

    def __try_load(self, model_size: model_sizes_str_t) -> Optional[model_sizes_str_t]:
        """
        Try to load a given model, set self.model and self.last_loaded_model_size if successful
        Args:
            model_size: requested model size

        Returns: model name if success else None

        """
        print(f"Trying to load model {model_size}")
        try:
            self.model = whisper.load_model(name=model_size, in_memory=self.unload_model_after_s)
            self.last_loaded_model_size = model_size
            print(f"Successfully loaded model '{model_size}'")
            return model_size

        except torch.cuda.OutOfMemoryError:
            print(f"Model '{model_size}' currently doesn't fit device.")
            return

    def load_model(self, requested_model_size: model_sizes_str_t = None) -> whisper.Whisper:
        """
        Load a model into memory. If no model size is specified, the largest model that currently fits the GPU is loaded
        
        Note: if requested_model_size doesn't fit, a smaller one will be chosen!
        Args:
            requested_model_size: size of the model to load - must fit on the GPU

        Returns: the loaded model, None if models does not fit on GPU

        Raises: NotImplementedError if no model fits on GPU (and CPU decoding is not implemented yet)

        """

        # get all potentially fitting models
        possible_sizes = self.get_possible_model_names_for_gpu()
        if len(possible_sizes) < 1:
            raise NotImplementedError("No model fits the GPU. CPU decoding is not implemented yet.")

        # check if correct model is already loaded
        if self.model is not None:
            # model is the requested one (and not None - prevents hiccups on first run)
            if requested_model_size == self.last_loaded_model_size and requested_model_size is not None:
                print(f"Target model '{requested_model_size}' already loaded")
                return self.model

            # TODO maybe prevent this case from happening again and again if max only fits in ideal circumstances
            # loaded model is the largest possible model
            elif self.last_loaded_model_size == possible_sizes[0]:
                print(f" Target model '{possible_sizes[0]}' already loaded")
                return self.model

            # we've got a not wanted model in our memory - purge it
            print(f"Got not wanted model in memory ('{self.last_loaded_model_size}'), unloading it...")
            self.__unload_model()

        # try to load the model asked for if given
        if requested_model_size is not None:
            print(f"Trying to load requested model size '{requested_model_size}'")

            # try to load model, if model is loaded return the set self.model
            if self.__try_load(requested_model_size) is not None:
                return self.model

            print(f"Requested model '{requested_model_size}' doesn't fit.")

        print("No model loaded. Trying to find the largest model that currently fits the GPU")
        print(f"LOAD. Current state: {self.last_loaded_model_size=}, {self.model=}")

        # iterate over all possible models, try to find the largest one that currently fits
        for model_size in possible_sizes:
            model_size = self.__try_load(model_size)
            if model_size is not None:
                break

        else:
            raise NotImplementedError("No model currently fits the GPU. CPU decoding is not implemented yet.")

        print(f"Model '{model_size}' loaded successfully!")

        return self.model

    def __run_model(self, audio_path: str, task: task_type_str_t,
                    source_language: Optional[str],
                    model_size: model_sizes_str_t = None,
                    auto_find_model_on_fail_to_load_target=True) -> Optional[WhisperResult]:
        """
        'Generic' function to run the model and centralize the needed logic
        This is used by transcribe() and translate()
        For args see transcribe() and translate()

        Returns:
            the result of the whisper models transcription/translation and the transcription time in seconds
        """

        # load model
        model = self.load_model(model_size)

        # if load failed try to find a better one if auto_find_model_on_fail_to_load_target is set
        if model is None:
            if not auto_find_model_on_fail_to_load_target:
                print("Could not load model, returning...")
                return None
            else:
                self.load_model()

        # start decoding
        start = dt.datetime.now()
        result = model.transcribe(audio_path, language=source_language, task=task)
        end = dt.datetime.now()
        return WhisperResult(**result, start_time=start, end_time=end, used_model_size=self.last_loaded_model_size)

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
