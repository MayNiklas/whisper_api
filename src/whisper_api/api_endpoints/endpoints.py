from asyncio import tasks
from multiprocessing.connection import Connection
from tempfile import NamedTemporaryFile
from typing import Union, Optional

import ffmpeg
from fastapi import APIRouter, Request, UploadFile, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from whisper_api.data_models.temp_dict import TempDict
from whisper_api.data_models.data_types import uuid_hex_t, task_type_str_t, named_temp_file_name_t
from whisper_api.data_models.task import Task, TaskResponse

V1_PREFIX = "/api/v1"


class EndPoints:
    def __init__(self, app: FastAPI,
                 tasks_dict: TempDict[uuid_hex_t, Task],
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
        self.app.add_api_route(f"{V1_PREFIX}/userinfo", self.userinfo)
        self.app.add_api_route(f"{V1_PREFIX}/srt", self.srt)

    def add_task(self, task: Task):
        self.tasks[task.uuid] = task

    def delete_task(self, task_id: uuid_hex_t):
        del self.tasks[task_id]

    async def status(self, task_id: uuid_hex_t) -> TaskResponse:
        """
        Get the status of a task.
        :param task_id: ID of the task.
        :return: Status of the task.
        """
        task = self.tasks.get(task_id, None)
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
        if file.filename is not None:
            task = Task(named_file.name, source_language, task_type, original_file_name=file.filename)
        else:
            task = Task(named_file.name, source_language, task_type)
        self.add_task(task)

        # send task into queue
        task_dict = {"task_name": "decode", "data": task.to_json}
        self.conn_to_child.send(task_dict)

        return task

    async def srt(self, task_id: uuid_hex_t):
        """
        Get the SRT file of a task.
        :param task_id: ID of the task.
        :return: SRT file of the task.
        """
        task = self.tasks.get(task_id, None)
        # TODO maybe hold a set of tasks that were present but aren't any more for better message?
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="task_id not found",
            )

        # TODO better way for central declaration of those states
        if task.status in ["pending", "processing", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=task.to_transmit_full,
            )

        headers = {
            "Content-Disposition": f"attachment; "
                                   f"filename={task.original_file_name}_{task.whisper_result.output_language}.srt",
            "Content-Type": "text/plain",
        }

        srt_buffer = task.whisper_result.get_srt_buffer()
        return StreamingResponse(iter(srt_buffer.readline, ""), headers=headers)

    async def transcribe(self, file: UploadFile, language: Optional[str] = None):
        task = await self.__start_task(file, language, "transcribe")

        return task.to_transmit_full

    async def translate(self, file: UploadFile, language: Optional[str] = None):

        task = await self.__start_task(file, language, "translate")

        return task.to_transmit_full

    async def userinfo(self, request: Request = None):

        return self.get_userinfo(request)

    @staticmethod
    def get_userinfo(request: Request = None) -> dict[str, str, str]:
        """
        Get user info from request headers.
        :param request: request object
        :return: dict with user info
        """
        user = {}

        if request.headers.get('X-Email'):
            user['email'] = request.headers.get('X-Email')

        if request.headers.get('X-User'):
            user['user'] = request.headers.get('X-User')

        user['user_agent'] = request.headers.get('User-Agent')

        return user

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
