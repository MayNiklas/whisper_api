from dataclasses import dataclass
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Union
from uuid import uuid4

from fastapi import UploadFile
from pydantic import BaseModel


class TaskResponse(BaseModel):
    task_id: str
    transcript: str
    language: str
    status: str
    time_uploaded: datetime
    processing_time: datetime
    time_processing_finished: datetime


@dataclass
class Task:
    audiofile: Union[UploadFile, NamedTemporaryFile]
    language: str
    status: str = "pending"
    result: dict = None
    time_uploaded: datetime = None
    time_processing_started = None
    time_processing_finished = None

    def __post_init__(self):
        # write content of given file into a temporary file
        if isinstance(self.audiofile, UploadFile):
            named_temp_file = NamedTemporaryFile()
            named_temp_file.write(await self.audiofile.read())
            self.audiofile: NamedTemporaryFile = named_temp_file
        self.uuid = uuid4().hex
        self.result = {}
        self.time_uploaded = self.time_uploaded or datetime.now()
        self.time_processing_started = None
        self.time_processing_finished = None

    @property
    def to_transmit_full(self) -> TaskResponse:
        if self.status == "pending" or self.status == "processing":
            return TaskResponse(
                task_id=self.uuid, time_uploaded=self.time_uploaded, status=self.status
            )

        return TaskResponse(
            task_id=self.uuid,
            transcript=self.result["text"],
            language=self.result["language"],
            status=self.status,
            time_uploaded=self.time_uploaded,
            processing_time=self.time_processing_started,
            time_processing_finished=self.time_processing_finished,
        )
