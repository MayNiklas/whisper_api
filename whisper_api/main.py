import asyncio

from fastapi import FastAPI
from fastapi import UploadFile

from .objects import Task
from .objects import tasks

app = FastAPI()


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


async def periodic():
    """
    Periodically run this function.
    """
    while True:
        # check for pending tasks every second
        await asyncio.sleep(1)

        # to keep track of whether we did anything
        done_something = False

        for task in tasks:
            if task.status == "pending":
                print("Processing task: {}".format(task.uuid))
                # TODO: make this non-blocking
                task.process()
                print("Finished processing task: {}".format(task.uuid))
                done_something = True

            if done_something:
                print("Done processing tasks.")


@app.on_event("startup")
async def schedule_periodic():
    """
    Schedule the periodic function to run every seconds.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(periodic())
