import glob
import zipfile
from multiprocessing.connection import Connection
from tempfile import NamedTemporaryFile
from typing import Optional

import ffmpeg
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from whisper_api.data_models.data_types import named_temp_file_name_t
from whisper_api.data_models.data_types import task_type_str_t
from whisper_api.data_models.data_types import uuid_hex_t
from whisper_api.data_models.decoder_state import DecoderState
from whisper_api.data_models.task import Task
from whisper_api.data_models.task import TaskResponse
from whisper_api.data_models.temp_dict import TempDict
from whisper_api.environment import AUTHORIZED_MAILS
from whisper_api.environment import LOG_DIR
from whisper_api.log_setup import logger

V1_PREFIX = "/api/v1"


class EndPoints:
    def __init__(self, app: FastAPI,
                 tasks_dict: TempDict[uuid_hex_t, Task],
                 decoder_state: DecoderState,
                 open_audio_files_dict: dict[named_temp_file_name_t, NamedTemporaryFile],
                 conn_to_child: Connection):
        self.tasks = tasks_dict
        self.decoder_state = decoder_state
        self.open_audio_files_dict = open_audio_files_dict
        self.app = app
        self.conn_to_child = conn_to_child

        self.add_endpoints()

    def add_endpoints(self):
        self.app.add_api_route(f"{V1_PREFIX}/status", self.status)
        self.app.add_api_route(f"{V1_PREFIX}/decoder_status", self.decoder_status)
        self.app.add_api_route(f"{V1_PREFIX}/decoder_status_refresh", self.decoder_status_refresh)
        self.app.add_api_route(f"{V1_PREFIX}/translate", self.translate, methods=["POST"])
        self.app.add_api_route(f"{V1_PREFIX}/transcribe", self.transcribe, methods=["POST"])
        self.app.add_api_route(f"{V1_PREFIX}/userinfo", self.userinfo)
        self.app.add_api_route(f"{V1_PREFIX}/login", self.login)
        self.app.add_api_route(f"{V1_PREFIX}/srt", self.srt)
        if AUTHORIZED_MAILS:
            self.app.add_api_route(f"{V1_PREFIX}/logs", self.get_logs)

    def add_task(self, task: Task):
        self.tasks[task.uuid] = task

    def delete_task(self, task_id: uuid_hex_t):
        del self.tasks[task_id]

    async def decoder_status(self):
        """ Get the last reported status of the decoder """
        # TODO: should this be some kind of admin route?
        #  hm... guess there is no downside in leaving it public
        return self.decoder_state

    async def decoder_status_refresh(self):
        """ trigger a refresh of the decoder - the response will NEITHER await nor include the new state """
        self.conn_to_child.send({
            "type": "status",
        })
        return "Request to refresh state is sent to decoder"

    async def status(self, task_id: uuid_hex_t) -> TaskResponse:
        """
        Get the status of a task.
        :param task_id: ID of the task.
        :return: Status of the task.
        """
        task = self.tasks.get(task_id, None)
        if task is None:
            logger.info(f"task_id '{task_id}' not found")
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
            logger.info(f"File '{named_file.name}' has no audio track.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File has no audio track."
            )

        self.open_audio_files_dict[named_file.name] = named_file
        if file.filename is not None:
            task = Task(
                audiofile_name=named_file.name,
                source_language=source_language,
                task_type=task_type,
                original_file_name=file.filename
            )
        else:
            task = Task(
                audiofile_name=named_file.name,
                source_language=source_language,
                task_type=task_type
            )
        self.add_task(task)

        # send task into queue
        # TODO: find out of json serialization is really needed
        task_dict = {"type": "decode", "data": task.to_json}
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
            logger.info(f"task_id '{task_id}' not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="task_id not found",
            )

        # TODO better way for central declaration of those states
        if task.status in ["pending", "processing", "failed"]:
            logger.info(f"task_id '{task_id}' not ready or failed, status: '{task.status}'")
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

    async def get_logs(self, request: Request):

        self.verify_user_mail(request)

        zip_archive = f"{LOG_DIR}/logs.zip"

        with zipfile.ZipFile(zip_archive, 'w', zipfile.ZIP_DEFLATED) as zipf:

            for file in glob.glob(LOG_DIR + '/*.log*'):
                # Add file to zip
                zipf.write(file)

        return FileResponse(zip_archive)

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
    def verify_user_mail(request: Request):
        user = EndPoints.get_userinfo(request)
        localhost_options = {"localhost", "127.0.0.1"}
        if request.base_url.hostname in localhost_options and request.client.host in localhost_options:
            return True

        if user.get("email") not in AUTHORIZED_MAILS:
            raise HTTPException(401, "Your mail is not in the whitelist")

        return user["email"]

    @staticmethod
    def login(request: Request):
        """
        /api/v1/login is a protected path.
        -> create a session cookie after successful login.
        -> redirect to parameter 'redirect' or '/app/'.
        """
        return RedirectResponse(url=request.query_params.get('redirect', '/app/'))

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
            logger.warning(e.stderr)
            return False
