from fastapi import FastAPI
from fastapi import UploadFile

from .models import Task

app = FastAPI()


# List of tasks - TODO: this is very temporary!
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
            if task.status != "done":
                return {
                    "task_id": task.uuid,
                    "time_uploaded": task.time_uploaded,
                    "status": task.status,
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


# needs to always be running in the background while having access to Tasks
@app.get("/v1/work")
async def work():
    """
    Start the background task.
    """
    for task in tasks:
        if task.status == "pending":
            task.process()
    return {"status": "done"}
