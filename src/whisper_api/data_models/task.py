import datetime as dt
import io
import os
from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from typing import Optional
from typing import Union
from uuid import uuid4

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass
from whisper.utils import WriteSRT
from whisper_api.data_models.data_types import model_sizes_str_t
from whisper_api.data_models.data_types import named_temp_file_name_t
from whisper_api.data_models.data_types import status_str_t
from whisper_api.data_models.data_types import task_type_str_t
from whisper_api.data_models.data_types import uuid_hex_t


class TaskResponse(BaseModel):
    """ The class that is returned via the API"""
    task_id: str
    transcript: Optional[str]
    source_language: Optional[str]
    task_type: task_type_str_t
    status: str
    position_in_queue: Optional[int]
    time_uploaded: dt.datetime
    processing_duration: Optional[int]
    time_processing_finished: Optional[dt.datetime]
    target_model_size: Optional[str]
    used_model_size: Optional[str]
    used_device: Optional[str]


@pydantic_dataclass
class WhisperResult:
    """ The result of a whisper translation/ transcription plus additional information"""
    text: str
    language: str  # spoken language
    output_language: str  # language code of the output language (hopefully)  # TODO validate that always true
    segments: list[dict[str, Union[float, str, int, list[int]]]]
    used_model_size: model_sizes_str_t
    start_time: dt.datetime
    end_time: dt.datetime
    used_device: str

    @property
    def processing_duration_s(self) -> int:
        return (self.end_time - self.start_time).seconds

    def get_srt_buffer(self) -> io.StringIO:
        """ The result text in SRT format """
        # setup buffer
        buffer = io.StringIO()
        # ResultWriter base-class requires an output directory
        # but WriteSRT's write_result function doesn't use it, it prints straight to the given buffer
        srt_writer = WriteSRT("/tmp")

        # trigger writing
        srt_writer.write_result(self.__dict__, buffer)

        # reset file pointer to the beginning of file
        buffer.seek(0)

        return buffer


@dataclass
class Task:
    audiofile_name: named_temp_file_name_t
    source_language: Optional[str]
    task_type: task_type_str_t
    status: status_str_t = "pending"
    position_in_queue = None
    whisper_result: Optional[WhisperResult] = None
    time_uploaded: dt.datetime = None
    uuid: uuid_hex_t = None
    target_model_size: Optional[model_sizes_str_t] = None
    original_file_name: str = "unknown"
    used_device: str = "unknown"

    def __post_init__(self):
        self.uuid = self.uuid or uuid4().hex
        self.time_uploaded = self.time_uploaded or dt.datetime.now()

    @property
    def to_transmit_full(self) -> TaskResponse:
        # TODO extract that list to a better place
        if self.status in ["pending", "processing", "failed"]:
            return TaskResponse(
                task_id=self.uuid,
                time_uploaded=self.time_uploaded,
                status=self.status,
                position_in_queue=self.position_in_queue,
                task_type=self.task_type,
            )

        # task status = "finished"
        return TaskResponse(
            task_id=self.uuid,
            transcript=self.whisper_result.text,
            source_language=self.whisper_result.language,
            task_type=self.task_type,
            status=self.status,
            position_in_queue=self.position_in_queue,
            time_uploaded=self.time_uploaded,
            processing_duration=self.whisper_result.processing_duration_s,
            time_processing_finished=self.whisper_result.end_time,
            target_model_size=self.target_model_size,
            used_model_size=self.whisper_result.used_model_size,
            used_device=self.whisper_result.used_device
        )

    @property
    def to_json(self) -> dict:
        json_cls = {**self.__dict__,
                    "whisper_result": self.whisper_result.__dict__ if self.whisper_result else None,
                    "audiofile_name": self.audiofile_name
                    }

        return json_cls

    @staticmethod
    def from_json(serialized_task: dict) -> "Task":
        """ Create a Task object from a json dict """
        whisper_result = serialized_task["whisper_result"]
        json_cls = {**serialized_task,
                    "whisper_result": WhisperResult(**whisper_result) if whisper_result else None,
                    "audiofile_name": serialized_task["audiofile_name"]
                    }

        return Task(**json_cls)


if __name__ == '__main__':
    t = Task(NamedTemporaryFile().name, "en", "transcribe")
    t.whisper_result = WhisperResult(text="hello",
                                     language="en",
                                     # segments=[],
                                     start_time=dt.datetime.now(),
                                     end_time=dt.datetime.now(),
                                     used_model_size="base")
    serialized = t.to_json
    new_task = Task.from_json(serialized)

    print(new_task)
    print(t == new_task)
