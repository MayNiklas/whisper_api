from dataclasses import dataclass
import datetime as dt
from tempfile import NamedTemporaryFile
from typing import Union, Optional
from uuid import uuid4

from fastapi import UploadFile
from pydantic import BaseModel

from whisper_api.data_models.data_types import status_str_t, task_type_str_t


class TaskResponse(BaseModel):
    task_id: str
    transcript: Optional[str]
    source_language: Optional[str]
    task_type: task_type_str_t
    status: str
    time_uploaded: dt.datetime
    processing_time: Optional[dt.datetime]
    time_processing_finished: Optional[dt.datetime]


@dataclass
class Task:
    audiofile: NamedTemporaryFile
    source_language: Optional[str]
    task_type: task_type_str_t
    status: status_str_t = "pending"
    result: dict = None
    time_uploaded: dt.datetime = None
    time_processing_started: Optional[dt.datetime] = None
    time_processing_finished: Optional[dt.datetime] = None

    def __post_init__(self):
        self.uuid = uuid4().hex
        self.result = {}
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
            transcript=self.result["text"],
            source_language=self.result["language"],
            task_type=self.task_type,
            status=self.status,
            time_uploaded=self.time_uploaded,
            processing_time=self.time_processing_started,
            time_processing_finished=self.time_processing_finished,
        )
