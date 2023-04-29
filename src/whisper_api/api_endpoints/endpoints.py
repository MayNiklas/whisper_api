from asyncio import tasks
from multiprocessing.connection import Connection
from tempfile import NamedTemporaryFile
from typing import Union, Optional

from fastapi import APIRouter, UploadFile, FastAPI, HTTPException, status
from pydantic import BaseModel
from starlette.responses import HTMLResponse, FileResponse

from whisper_api.data_models.data_types import uuid_hex_t, task_type_str_t
from whisper_api.data_models.task import Task, TaskResponse

V1_PREFIX = "/api/v1"


class EndPoints:
    def __init__(self, app: FastAPI, tasks_dict: dict[uuid_hex_t, Task], conn_to_child: Connection):
        self.tasks = tasks_dict
        self.app = app
        self.conn_to_child = conn_to_child

        self.add_endpoints()

    def add_endpoints(self):
        self.app.add_api_route(f"{V1_PREFIX}/status", self.status)
        self.app.add_api_route(f"{V1_PREFIX}/translate", self.translate, methods=["POST"])
        self.app.add_api_route(f"{V1_PREFIX}/transcribe", self.transcribe, methods=["POST"])

    def add_task(self, task):
        self.tasks[task.uuid] = task

    def get_task(self, task_id):
        return self.tasks[task_id]

    def delete_task(self, task_id):
        del self.tasks[task_id]

    async def status(self, task_id: str) -> TaskResponse:
        """
        Get the status of a task.
        :param task_id: ID of the task.
        :return: Status of the task.
        """
        task = self.get_task(task_id, None)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="task_id not valid",
            )

        return task.to_transmit_full

    async def __upload_file_to_named_temp_file(self, file: UploadFile) -> NamedTemporaryFile:
        named_temp_file = NamedTemporaryFile()
        named_temp_file.write(await file.read())
        return named_temp_file

    async def __start_task(self, file: UploadFile, source_language: str, task_type: task_type_str_t) -> Task:

        named_file = await self.__upload_file_to_named_temp_file(file)
        self.open_audio_files[named_file.name] = named_file
        task = Task(named_file, source_language, task_type)
        self.add_task(task)

        self.conn_to_child.send(
            {"uuid": task.uuid, "file": task.audiofile_name.name, "action": task_type, "language": task.source_language}
        )

        return task

    async def transcribe(self, file: UploadFile, source_language: Optional[str] = None):

        # validate that the file is an audio file
        if not file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file is not an audio file",
            )

        task = await self.__start_task(file, source_language, "transcribe")

        return task.to_transmit_full

    async def translate(self, file: UploadFile, source_language: Optional[str] = None):
        if source_language is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="language not specified",
            )

        task = await self.__start_task(file, source_language, "translate")

        return task.to_transmit_full




