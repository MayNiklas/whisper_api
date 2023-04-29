import multiprocessing
import os
import sys
from tempfile import NamedTemporaryFile

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from whisper_api.api_endpoints.endpoints import EndPoints
from whisper_api.data_models.data_types import named_temp_file_name_t, uuid_hex_t
from whisper_api.data_models.task import Task

if __package__ is None and not hasattr(sys, "frozen"):
    import os.path

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))


from whisper_api.environment import API_PORT, API_LISTEN, KEEP_MODEL_IN_MEMORY
from whisper_api.version import __version__
from whisper_api.api_endpoints import endpoints

import whisper_api.decoding.decoder as decoder

description = """
Whisper API transcribes audio files.
"""

task_dict: dict[uuid_hex_t, Task] = {}
# TODO: implement closing of file in callback function
open_audio_files_dict: dict[named_temp_file_name_t, NamedTemporaryFile] = {}

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
conn_to_parent, conn_to_child = multiprocessing.Pipe(duplex=True)

api_end_points = EndPoints(app, task_dict, open_audio_files_dict, conn_to_child)


@app.on_event("startup")
def listen_to_child():
    """ Start decode-process, listen to it and update the task_dict accordingly """

    decoder_process = multiprocessing.Process(target=decoder.Decoder.init_and_run,
                                              args=(conn_to_child, conn_to_parent, KEEP_MODEL_IN_MEMORY)
                                              )
    decoder_process.start()

    while True:
        task_update_json = conn_to_parent.recv()
        task = Task.from_json(task_update_json)

        task_dict[task.uuid] = task

        # when task is done (no matter if finished or failed) close and delete the audio file
        if task.status == "finished" or task.status == "failed":
            open_audio_files_dict[task.audiofile_name].close()
            del open_audio_files_dict[task.audiofile_name]


def start():
    import uvicorn

    uvicorn.run(app, host=API_LISTEN, port=API_PORT)
