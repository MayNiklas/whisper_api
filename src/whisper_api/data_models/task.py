from dataclasses import dataclass
from datetime import datetime
from typing import Union
from uuid import uuid4

from pydantic import BaseModel


class TaskInProcessOrPending(BaseModel):
    task_id: str
    time_uploaded: datetime
    status: str


class TaskResult(BaseModel):
    task_id: str
    transcript: str
    language: str
    status: str
    processing_time: float


@dataclass
class Task:
    audiofile: str
    language: str
    status: str
    result: dict
    time_uploaded: datetime = None
    time_processing_started = None
    time_processing_finished = None

    def __post_init__(self):
        self.uuid = uuid4()
        self.audiofile = ""
        self.language = ""
        self.status = "pending"
        self.result = {}
        self.time_uploaded = self.time_uploaded or datetime.now()
        self.time_processing_started = None
        self.time_processing_finished = None

    @property
    def to_transmit_full(self) -> Union[TaskInProcessOrPending, TaskResult]:
        if self.status == "pending" or self.status == "processing":
            return TaskInProcessOrPending(
                task_id=self.uuid, time_uploaded=self.time_uploaded, status=self.status
            )

        return TaskResult(
            task_id=self.uuid,
            transcript=self.result["text"],
            language=self.result["language"],
            status=self.status,
            processing_time=self.time_processing_finished - self.time_processing_started,
        )
