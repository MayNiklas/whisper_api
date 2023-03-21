import asyncio
import multiprocessing
from multiprocessing import freeze_support
from multiprocessing import Pool
from tempfile import NamedTemporaryFile

from fastapi import FastAPI
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse

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

# needs to be improved - this is just a quick fix

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# create Pipe for communication between main and worker thread
conn1, conn2 = multiprocessing.Pipe(duplex=True)


def worker(pipe):
    """
    Worker thread.
    :param pipe: Pipe to communicate with the main thread.
    """

    from . import convert

    while True:
        job = pipe.recv()
        pipe.send(
            {
                "uuid": job["uuid"],
                "result": convert.transcribe(job["file"], job["language"]),
            }
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

    # send file to worker thread
    conn2.send(
        {"uuid": task.uuid, "file": task.audiofile.name, "language": task.language}
    )

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
            if task.status == "pending" or task.status == "processing":
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
                    "language": task.result["language"],
                    "transcript": task.result["text"],
                }


# serve static folder
@app.get("/{file_path:path}")
async def static(file_path: str):
    """
    Serve static files e.g. the frontend.
    :param file_path: Path to the file.
    :return: File.
    """

    if file_path == "":
        file_path = "index.html"

    allowed_files = ["index.html", "script.js", "styles.css"]

    # return 404 if not in allowed files
    if file_path not in allowed_files:
        return HTMLResponse(status_code=404, content="404 Not Found")

    return FileResponse(f"static/{file_path}")


async def process_tasks():
    """
    Start background process and receive results from the worker thread.
    """

    # create worker thread
    p = multiprocessing.Process(target=worker, args=(conn1,))
    p.start()

    while True:
        # check for pending tasks every second
        await asyncio.sleep(0.25)

        # check if there is a result from the worker thread
        if conn2.poll(0.1):
            res = conn2.recv()

            task = next((task for task in tasks if task.uuid == res["uuid"]), None)
            task.result = res["result"]
            task.status = "done"
            task.audiofile.close()

            print("Task done: " + str(task.uuid))


@app.on_event("startup")
async def startup():
    """
    Get's executed on startup.
    """

    loop = asyncio.get_event_loop()
    loop.create_task(process_tasks())
