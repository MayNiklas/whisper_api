from fastapi import FastAPI, UploadFile

from .models import Task

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
    # Task contains a temporary file to store the audio file
    # and a unique identifier
    task = Task()
    task.audiofile.write(await file.read())

    tasks.append(task)

    return {"task_id": task.uuid}
