import multiprocessing
import signal
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
parent_side, child_side = multiprocessing.Pipe()

api_end_points = EndPoints(app, task_dict, open_audio_files_dict, parent_side)


@app.on_event("startup")
def listen_to_child():
    """ Start decode-process, listen to it and update the task_dict accordingly """

    def signal_worker_to_exit():
        """ Terminate child and hope it dies """
        print("Shutting down decoder process...")
        decoder_process.terminate()
        decoder_process.join()
        print("Child is dead.")

    # start child
    decoder_process = multiprocessing.Process(target=decoder.Decoder.init_and_run,
                                              args=(child_side, KEEP_MODEL_IN_MEMORY),
                                              name="Decoder-Process",
                                              daemon=True
                                              )
    decoder_process.start()

    # register handlers to kill it
    signal.signal(signal.SIGINT, signal_worker_to_exit)  # Handle Control + C
    signal.signal(signal.SIGTERM, signal_worker_to_exit)  # Handle 'kill' command
    signal.signal(signal.SIGHUP, signal_worker_to_exit)  # Handle terminal closure

    while True:
        try:
            task_update_json = parent_side.recv()
        except KeyboardInterrupt:
            signal_worker_to_exit()
            exit(0)

        task = Task.from_json(task_update_json)

        task_dict[task.uuid] = task

        # when task is done (no matter if finished or failed) close and delete the audio file
        if task.status == "finished" or task.status == "failed":
            open_audio_files_dict[task.audiofile_name].close()
            del open_audio_files_dict[task.audiofile_name]


def start():
    import uvicorn

    uvicorn.run(app, host=API_LISTEN, port=API_PORT)
