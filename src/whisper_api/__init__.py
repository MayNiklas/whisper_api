import multiprocessing
import signal
import sys
import threading
from tempfile import NamedTemporaryFile
from typing import Callable

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from whisper_api.api_endpoints.endpoints import EndPoints
from whisper_api.data_models.threadsafe_dict import ThreadSafeDict
from whisper_api.data_models.data_types import named_temp_file_name_t, uuid_hex_t
from whisper_api.data_models.task import Task

if __package__ is None and not hasattr(sys, "frozen"):
    import os.path

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))


from whisper_api.environment import API_PORT, API_LISTEN, UNLOAD_MODEL_AFTER_S
from whisper_api.version import __version__
from whisper_api.api_endpoints import endpoints

import whisper_api.decoding.decoder as decoder

description = """
Whisper API transcribes audio files.
"""

print(description)


"""
init global variables
"""

task_dict: ThreadSafeDict[uuid_hex_t, Task] = ThreadSafeDict()
# TODO: implement closing of file in callback function
open_audio_files_dict: ThreadSafeDict[named_temp_file_name_t, NamedTemporaryFile] = ThreadSafeDict()


"""
Init API
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

"""
Setup decoder process
"""

# create Pipe for communication between main and worker thread
parent_side, child_side = multiprocessing.Pipe()

api_end_points = EndPoints(app, task_dict, open_audio_files_dict, parent_side)


def listen_to_decoder(pipe_to_listen_to: multiprocessing.connection.Connection,
                      worker_exit_fn: Callable[[], None]):
    """ listen to decode process and update the task_dict accordingly """
    while True:
        try:
            task_update_json = pipe_to_listen_to.recv()
        except KeyboardInterrupt:
            worker_exit_fn()
            exit(0)

        task = Task.from_json(task_update_json)

        task_dict[task.uuid] = task

        # when task is done (no matter if finished or failed) close and delete the audio file
        if task.status == "finished" or task.status == "failed":
            open_audio_files_dict[task.audiofile_name].close()
            del open_audio_files_dict[task.audiofile_name]


"""
Dispatch decoder process and listener thread
"""


# do this all after API has started, so the init of the initial process is done
# otherwise we get this beautiful RuntimeError:
# 'An attempt has been made to start a new process before the
# current process has finished its bootstrapping phase'
@app.on_event("startup")
def setup_decoder_process_and_listener_thread():
    """
    Handles the whole multiprocessing and threading stuff to get:
    - a decoder process
    - a listener thread for the pipe to the decoder process
    """

    def signal_worker_to_exit():
        """ Terminate child and hope it dies """
        print("Shutting down decoder process...")
        decoder_process.terminate()
        decoder_process.join()
        print("Child is dead.")

    # start decoder process
    decoder_process = multiprocessing.Process(target=decoder.Decoder.init_and_run,
                                              args=(child_side, UNLOAD_MODEL_AFTER_S),
                                              name="Decoder-Process",
                                              daemon=True
                                              )
    decoder_process.start()

    # register handlers to kill it
    signal.signal(signal.SIGINT, signal_worker_to_exit)  # Handle Control + C
    signal.signal(signal.SIGTERM, signal_worker_to_exit)  # Handle 'kill' command
    signal.signal(signal.SIGHUP, signal_worker_to_exit)  # Handle terminal closure

    # start thread to listen to decoder process pipe
    decoder_process_listen_thread = threading.Thread(target=listen_to_decoder,
                                                     args=(parent_side, signal_worker_to_exit),
                                                     name="Decoder-Listen-Thread",
                                                     daemon=True)
    decoder_process_listen_thread.start()


"""
Hook for uvicorn
"""


def start():
    import uvicorn

    uvicorn.run(app, host=API_LISTEN, port=API_PORT)
