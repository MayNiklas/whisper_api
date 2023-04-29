from dataclasses import dataclass
import datetime as dt
from tempfile import NamedTemporaryFile
from typing import Union, Optional
from uuid import uuid4

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from whisper_api.data_models.data_types import status_str_t, task_type_str_t, named_temp_file_name_t


class TaskResponse(BaseModel):
    """ The class that is returned via the API"""
    task_id: str
    transcript: Optional[str]
    source_language: Optional[str]
    task_type: task_type_str_t
    status: str
    time_uploaded: dt.datetime
    processing_time: int
    time_processing_finished: Optional[dt.datetime]


@pydantic_dataclass
class TaskResult:
    """ The result of a whisper translation/ transcription plus additional information"""
    text: str
    language: str
    segment_level_details: list[dict[str, int]]
    start_time: dt.datetime
    end_time: dt.datetime

    @property
    def processing_time_s(self) -> int:
        return (self.end_time - self.start_time).seconds


@dataclass
class Task:
    audiofile_name: named_temp_file_name_t
    source_language: Optional[str]
    task_type: task_type_str_t
    status: status_str_t = "pending"
    whisper_result: Optional[TaskResult] = None
    time_uploaded: dt.datetime = None

    def __post_init__(self):
        self.uuid = uuid4().hex
        self.time_uploaded = self.time_uploaded or dt.datetime.now()
        self.time_processing_started = None
        self.time_processing_finished = None

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
            processing_time=self.whisper_result.processing_time_s,
            time_processing_finished=self.whisper_result.end_time,
        )
