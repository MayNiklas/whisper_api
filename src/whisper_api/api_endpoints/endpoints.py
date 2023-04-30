from asyncio import tasks
from multiprocessing.connection import Connection
from tempfile import NamedTemporaryFile
from typing import Union, Optional

import ffmpeg
from fastapi import APIRouter, UploadFile, FastAPI, HTTPException, status
from pydantic import BaseModel
from starlette.responses import HTMLResponse, FileResponse

from whisper_api.data_models.data_types import uuid_hex_t, task_type_str_t, named_temp_file_name_t
from whisper_api.data_models.task import Task, TaskResponse

V1_PREFIX = "/api/v1"


class EndPoints:
    def __init__(self, app: FastAPI,
                 tasks_dict: dict[uuid_hex_t, Task],
                 open_audio_files_dict: dict[named_temp_file_name_t, NamedTemporaryFile],
                 conn_to_child: Connection):
        self.tasks = tasks_dict
        self.open_audio_files_dict = open_audio_files_dict
        self.app = app
        self.conn_to_child = conn_to_child

        self.add_endpoints()

    def add_endpoints(self):
        self.app.add_api_route(f"{V1_PREFIX}/status", self.status)
        self.app.add_api_route(f"{V1_PREFIX}/translate", self.translate, methods=["POST"])
        self.app.add_api_route(f"{V1_PREFIX}/transcribe", self.transcribe, methods=["POST"])

    def add_task(self, task: Task):
        self.tasks[task.uuid] = task

    def get_task(self, task_id: uuid_hex_t):
        return self.tasks[task_id]

    def delete_task(self, task_id: uuid_hex_t):
        del self.tasks[task_id]

    async def status(self, task_id: uuid_hex_t) -> TaskResponse:
        """
        Get the status of a task.
        :param task_id: ID of the task.
        :return: Status of the task.
        """
        task = self.get_task(task_id)
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

        # test that file has audio track
        if not self.is_file_audio(named_file.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File has no audio track."
            )

        self.open_audio_files_dict[named_file.name] = named_file
        task = Task(named_file.name, source_language, task_type)
        self.add_task(task)

        # send task into queue
        task_dict = {"task_name": "decode", "data": task.to_json}
        self.conn_to_child.send(task_dict)

        return task

    async def transcribe(self, file: UploadFile, language: Optional[str] = None):
        task = await self.__start_task(file, language, "transcribe")

        return task.to_transmit_full

    async def translate(self, file: UploadFile, language: Optional[str] = None):

        task = await self.__start_task(file, language, "translate")

        return task.to_transmit_full

    @staticmethod
    def is_file_audio(file_path: str) -> bool:
        """
        Check if the file contains audio stream.
        :param file_path: path to file
        :return: True if file contains audio, False otherwise.
        """

        try:
            probe = ffmpeg.probe(file_path)
            audio_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            return audio_stream is not None

        except ffmpeg.Error as e:
            print(e.stderr)
            return False

