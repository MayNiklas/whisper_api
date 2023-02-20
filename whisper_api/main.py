from fastapi import FastAPI, UploadFile

from .models import Task
from . import convert

app = FastAPI()

DEFAULT_MODEL = "large-v2"

# List of tasks
tasks = []


@app.post("/v1/transcribe")
async def transcribe(file: UploadFile):
    """
    Transcribe audio file.
    :param file: Uploaded audio file.
    :return: Transcription of audio file.
    """

    # Create a new task
    task = Task()
    task.audiofile.write(await file.read())

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
            return {"task_id": task.uuid, "status": task.status, "result": task.result}


@app.get("/v1/work")
async def work():
    """
    Get a task to work on.
    :return: Task to work on.
    """
    for task in tasks:
        if task.status == "pending":
            task.status = "working"

            result = convert.transcribe(task.audiofile.name)

    return {
        "language": result["language"],
        "transcript": result["text"],
    }
