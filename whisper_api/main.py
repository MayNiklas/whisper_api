import asyncio

from fastapi import FastAPI
from fastapi import UploadFile
from fastapi import responses

from .objects import Task
from .objects import tasks
from .version import __version__


description = """
Whisper API transcribes audio files.

## Users

You will be able to:

* **Create** a new task by uploading an audio file.
* **Read** the status of a task.
"""

app = FastAPI(
    title="Whisper API",
    description=description,
    version=__version__,
    # terms_of_service="PLACEHOLDER",
    contact={
        "name": "GitHub Repository",
        "url": "https://github.com/mayniklas/whisper_api/",
    },
)


@app.post("/v1/transcribe")
async def transcribe(file: UploadFile, language: str = None):
    """
    Transcribe audio file.
    :param file: Audio file to transcribe.
    :param language: Language of the audio file.

    :return: ID of the task.
    """

    # Create a new task
    task = Task()
    task.audiofile.write(await file.read())
    task.language = language

    # Append task to pool of tasks
    tasks.append(task)

    # return task id
    return {"task_id": task.uuid}


@app.get("/v1/status/{task_id}")
async def status(task_id: str):
    """
    Get the status of a task.
    :param task_id: ID of the task.
    :return: Status of the task.
    """
    for task in tasks:
        if str(task.uuid) == task_id:
            if task.status == "pending":
                return {
                    "task_id": task.uuid,
                    "time_uploaded": task.time_uploaded,
                    "status": task.status,
                }
            elif task.status == "pending":
                return {
                    "task_id": task.uuid,
                    "time_uploaded": task.time_uploaded,
                    "status": task.status,
                    "time_processing": task.time_processing,
                }
            else:
                return {
                    "task_id": task.uuid,
                    "time_uploaded": task.time_uploaded,
                    "status": task.status,
                    "time_processing": task.time_processing,
                    "time_finished": task.time_finished,
                    "compute_time": task.compute_time,
                    "language": task.result["language"],
                    "transcript": task.result["text"],
                }


@app.get("/v1/get_pending_task")
async def get_pending_task():
    """
    Get a pending task.
    :return: ID of the task.
    """
    for task in tasks:
        if task.status == "pending":
            return {
                "task_id": task.uuid,
                "language": task.language,
                "status": task.status,
            }


@app.get("/v1/get_task_audiofile/{task_id}")
async def get_task_audiofile(task_id: str):
    """
    Get the audio file of a task.
    :param task_id: ID of the task.
    :return: Audio file.
    """
    for task in tasks:
        if str(task.uuid) == task_id:
            # return audiofile stored at path task.audiofile.name
            return responses.FileResponse(task.audiofile.name)
