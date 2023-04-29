import datetime as dt
from multiprocessing.connection import Connection
from typing import Literal, Optional

import torch
import whisper

from whisper_api.data_models.data_types import model_sizes_str_t, task_type_str_t
from whisper_api.data_models.task import TaskResult

vram_model_map: dict[model_sizes_str_t, int] = {
    "large": 10,
    "medium": 5,
    "small": 2,
    "base": 1,
}


class Decoder:

    def __init__(self, task_pipe: Connection, conn_to_parent: Connection, keep_model_loaded: bool = True):
        """
        Holding and managing the whisper model
        Args:
            task_pipe: pipe to receive tasks from the parent process
            conn_to_parent: pipe to pass results to parent process
            keep_model_loaded: if model should be kept in memory after loading
        """
        self.task_queue = task_pipe
        self.conn_to_parent = conn_to_parent

        # TODO: do something useful with this (unloading model)
        self.keep_model_loaded = keep_model_loaded

        self.model: whisper.Whisper = None
        self.last_loaded_model_size: model_sizes_str_t = None

        if not torch.cuda.is_available():
            raise NotImplementedError("CPU decoding is not implemented yet")

        self.gpu_vram = torch.cuda.mem_get_info()[0]

    def get_max_model_name_for_gpu(self) -> Optional[model_sizes_str_t]:
        """
        Get the largest model that fits on the GPU
        Returns: name of the model

        """
        for model_name, model_size in vram_model_map.items():
            if self.gpu_vram >= model_size * 1e9:
                print(f"Max usable model: '{model_name}'")
                return model_name

    def load_model(self, model_size: model_sizes_str_t = None) -> Optional[whisper.Whisper]:
        """
        Load a model into memory. If no model size is specified, the largest model that fits the GPU is loaded.
        Args:
            model_size: size of the model to load - must fit on the GPU

        Returns: the loaded model

        """
        if model_size is None:
            print("No model size specified, trying to find the largest model that fits the GPU")
            model_size = self.get_max_model_name_for_gpu()
            if model_size is None:
                raise NotImplementedError("No model fits the GPU. CPU decoding is not implemented yet.")

        if self.model is not None and self.last_loaded_model_size == model_size:
            print(f" Target model '{model_size}' already loaded")
            return self.model

        print("Loading model...")
        try:
            # TODO: is this the right place to use keep_model_loaded?
            self.model = whisper.load_model(name=model_size, in_memory=self.keep_model_loaded)
            self.last_loaded_model_size = model_size

        except torch.cuda.OutOfMemoryError:
            print(f"Model '{model_size}' is too large for this device.")
            return

        print("Model loaded successfully!")

        return self.model

    def __run_model(self, audio_path: str, task: task_type_str_t,
                    source_language: Optional[str],
                    model_size: model_sizes_str_t = None) -> TaskResult:
        """
        'Generic' function to run the model and centralize the needed logic
        This is used by transcribe() and translate()
        For args see transcribe() and translate()

        Returns:
            the result of the whisper models transcription/translation and the transcription time in seconds
        """

        model = self.load_model(model_size)
        start = dt.datetime.now()
        result = model.transcribe(audio_path, language=source_language, task=task)
        end = dt.datetime.now()
        return TaskResult(**result, start_time=start, end_time=end)

    def transcribe(self, audio_path: str,
                   source_language: Optional[str],
                   model_size: model_sizes_str_t = None) -> TaskResult:
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
                  model_size: model_sizes_str_t = None) -> TaskResult:
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
