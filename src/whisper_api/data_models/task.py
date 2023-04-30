from dataclasses import dataclass
import datetime as dt
from tempfile import NamedTemporaryFile
from typing import Union, Optional
from uuid import uuid4

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from whisper_api.data_models.data_types import status_str_t, task_type_str_t, named_temp_file_name_t, uuid_hex_t, \
    model_sizes_str_t


class TaskResponse(BaseModel):
    """ The class that is returned via the API"""
    task_id: str
    transcript: Optional[str]
    source_language: Optional[str]
    task_type: task_type_str_t
    status: str
    time_uploaded: dt.datetime
    processing_duration: Optional[int]
    time_processing_finished: Optional[dt.datetime]


@pydantic_dataclass
class WhisperResult:
    """ The result of a whisper translation/ transcription plus additional information"""
    text: str
    language: str
    # segments: list[dict[str, int]]
    used_model_size: model_sizes_str_t
    start_time: dt.datetime
    end_time: dt.datetime

    @property
    def processing_duration_s(self) -> int:
        return (self.end_time - self.start_time).seconds


@dataclass
class Task:
    audiofile_name: named_temp_file_name_t
    source_language: Optional[str]
    task_type: task_type_str_t
    status: status_str_t = "pending"
    whisper_result: Optional[WhisperResult] = None
    time_uploaded: dt.datetime = None
    uuid: uuid_hex_t = None
    target_model_size: Optional[model_sizes_str_t] = None

    def __post_init__(self):
        self.uuid = self.uuid or uuid4().hex
        self.time_uploaded = self.time_uploaded or dt.datetime.now()

    @property
    def to_transmit_full(self) -> TaskResponse:
        if self.status == "pending" or self.status == "processing":
            return TaskResponse(
                task_id=self.uuid,
                time_uploaded=self.time_uploaded,
                status=self.status,
                task_type=self.task_type,
            )

        return TaskResponse(
            task_id=self.uuid,
            transcript=self.whisper_result.text,
            source_language=self.whisper_result.language,
            task_type=self.task_type,
            status=self.status,
            time_uploaded=self.time_uploaded,
            processing_duration=self.whisper_result.processing_duration_s,
            time_processing_finished=self.whisper_result.end_time,
            target_model_size=self.target_model_size

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
