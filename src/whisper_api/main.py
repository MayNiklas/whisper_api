import datetime as dt
import multiprocessing
import os
import random
import signal
import string
import sys
import threading
import time
from contextlib import asynccontextmanager
from tempfile import NamedTemporaryFile
from types import FrameType
from typing import Any
from typing import Callable
from typing import Optional

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

if __package__ is None and not hasattr(sys, "frozen"):

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import whisper_api.decoding.decoder as decoder
from whisper_api import __version__
from whisper_api.api_endpoints.endpoints import EndPoints
from whisper_api.data_models.data_types import named_temp_file_name_t
from whisper_api.data_models.data_types import uuid_hex_t
from whisper_api.data_models.decoder_state import DecoderState
from whisper_api.data_models.task import Task
from whisper_api.data_models.temp_dict import TempDict
from whisper_api.environment import API_LISTEN
from whisper_api.environment import API_PORT
from whisper_api.environment import DELETE_RESULTS_AFTER_M
from whisper_api.environment import LOG_DIR
from whisper_api.environment import LOG_FILE
from whisper_api.environment import MAX_MODEL
from whisper_api.environment import REFRESH_EXPIRATION_TIME_ON_USAGE
from whisper_api.environment import RUN_RESULT_EXPIRY_CHECK_M
from whisper_api.environment import UNLOAD_MODEL_AFTER_S
from whisper_api.environment import USE_GPU_IF_AVAILABLE
from whisper_api.frontend.endpoints import Frontend
from whisper_api.log_setup import configure_logging
from whisper_api.log_setup import logger
from whisper_api.log_setup import uuid_log_format

IS_MAIN_PROCESS = multiprocessing.current_process().name == "MainProcess"

description = """
Whisper API transcribes audio files.
"""

if IS_MAIN_PROCESS:
    print(description)


"""
init global variables
"""
if IS_MAIN_PROCESS:
    # TODO: can tasks get GCed before they finish if queue is too long?
    task_dict: TempDict[uuid_hex_t, Task] = TempDict(
        expiration_time_m=DELETE_RESULTS_AFTER_M,
        refresh_expiration_time_on_usage=REFRESH_EXPIRATION_TIME_ON_USAGE,
        auto_gc_interval_s=RUN_RESULT_EXPIRY_CHECK_M * 60,
    )

    open_audio_files_dict: dict[named_temp_file_name_t, NamedTemporaryFile] = dict()

    decoder_state = DecoderState()

    """
    Setup decoder process
    """

    # create Pipe for communication between main and worker thread
    parent_side, child_side = multiprocessing.Pipe()
    logging_entry_end, log_outry_end = multiprocessing.Pipe()

    configure_logging(logger, LOG_DIR, LOG_FILE, logging_entry_end)


def handle_message(message_type: str, data: dict[str, Any]):
    """
    Handles the received message from the decoder process.
    Args:
        message_type: type of the message
        data: the data that was sent with the message, must match the type of the message
    """
    if message_type == "status":
        # create uuid safe copy for log
        log_data = data.copy()
        log_data["queue_status"] = {uuid_log_format(k): v for k, v in data["queue_status"].items()}
        logger.info(f"Received status update: {log_data=}")

        # do the actual processing
        decoder_state.gpu_mode = data["gpu_mode"]
        decoder_state.max_model_to_use = data["max_model_to_use"]
        decoder_state.last_loaded_model_size = data["last_loaded_model_size"]
        decoder_state.is_model_loaded = data["is_model_loaded"]
        decoder_state.currently_busy = data["currently_busy"]
        # might not be always present in future development
        decoder_state.tasks_in_queue = data.get("tasks_in_queue")
        decoder_state.received_at = dt.datetime.now()

        # check if new position data arrived else continue
        if (queue_status := data.get("queue_status")) is None:
            return

        # refresh positions if new position-data is received
        for key, pos in queue_status.items():
            task_dict[key].position_in_queue = pos

        return

    if message_type == "task_update":  # data is a json-serialized task
        task: Task = Task.from_json(data)
        logger.info(
            f"Received task update for task.uuid={uuid_log_format(task.uuid)}, {task.status=}, {task.position_in_queue=}"
        )

        task_dict[task.uuid] = task

        # when task is done (no matter if finished or failed) close and delete the audio file
        if task.status == "finished" or task.status == "failed":
            open_audio_files_dict[task.audiofile_name].close()
            del open_audio_files_dict[task.audiofile_name]


def listen_to_decoder(pipe_to_listen_to: multiprocessing.connection.Connection, worker_exit_fn: Callable[[int], None]):
    """listen to decode process and update the task_dict accordingly"""

    def handle_keyboard_interrupt():
        logger.info("KeyboardInterrupt - initiating exit.")
        worker_exit_fn(signal.SIGINT)

    while True:
        try:
            if pipe_to_listen_to.poll(0.5):
                msg = pipe_to_listen_to.recv()
            # no messages left and stop threads is set
            elif _stop_threads:
                pipe_to_listen_to.close()
                logger.info(f"Flag to stop listener-thread is set. Ending thread.")
                return
            else:
                continue

        # TODO: is this even a case that can happen?
        #  pretty unsure since the function was flawed for a long time and should have produces a crash...
        except KeyboardInterrupt:
            handle_keyboard_interrupt()
            return

        # EOF is what happens when the pipe gets closed, so we use it to shut down the pipe
        # when the pipe is shut down we don't need that thread - obviously
        except EOFError:
            logger.info(f"Pipe closed (EOFError). Exiting thread.")
            return

        message_type = msg.get("type", None)
        data = msg.get("data", None)

        try:
            handle_message(message_type, data)

        except KeyboardInterrupt:
            handle_keyboard_interrupt()

        except Exception as e:
            # I'd love to print the full data, but that would potentially log the transcriptions, so not an option.
            logger.error(
                f"Exception '{type(e).__name__}': {e}, message_type={message_type!r}, data.keys()={list(data.keys())}"
            )


"""
Dispatch decoder process and listener thread
"""


# do this all after API has started, so the init of the initial process is done
# otherwise we get this beautiful RuntimeError:
# 'An attempt has been made to start a new process before the
# current process has finished its bootstrapping phase'
_stop_threads = False  # i hate this, but python doesn't offer any good way to kill a thread


def setup_decoder_process_and_listener_thread() -> Callable[[int], None]:
    """
    Handles the whole multiprocessing and threading stuff to get:
    - a decoder process
    - a listener thread for the pipe to the decoder process
    """

    def exit_fn(signum: int):
        """Terminate child and hope it dies"""
        global _stop_threads
        logger.warning(f"Got {signum=}")

        pid = decoder_process.pid

        logger.info(f"Shutting down decoder process {pid=}...")

        # try it using multiprocessing
        decoder_process.terminate()  # uses SIGTERM
        decoder_process.join(5)

        # is it alive? - use harder tools
        if decoder_process.is_alive():
            logger.info("Child did not die in time, trying to kill it using os...")
            os.kill(decoder_process.pid, signal.SIGKILL)

        decoder_process.join(2)  # wait again
        if decoder_process.is_alive():
            logger.error(f"Can't kill child {pid=}, giving up. Sorry.")
        else:
            logger.info("Child is dead.")

        # don't know if the part below here really brings anything valuable to the table
        # I assume it might because we give the thread the time to receive all messages before shutdown

        logger.info(f"Shutting down listener thread...")
        _stop_threads = True
        decoder_process_listen_thread.join(5)  # this should be more than enough time to empty message queue
        # faulthandler.dump_traceback_later(10, exit=True, file=sys.stdout)
        if decoder_process_listen_thread.is_alive():
            logger.warning(f"Can't shutdown listener gracefully, proceeding with shutdown")
        else:
            logger.info(f"Listener thread killed successfully")

        # at this point are still at least three threads going
        # - the gc thread in the task queue (daemon)
        # - the logger thread (registered in atexit)
        # - uvicorn (it'll be fine and have its own shutdown procedures)

        sys.exit(0)

    def signal_worker_to_exit(signum: int, frame: Optional[FrameType]):
        """
        wrapper around the exit function that provides the signature signal.signal() requires as second parameter
        https://docs.python.org/3/library/signal.html#signal.signal
        https://stackoverflow.com/questions/18704862/python-frame-parameter-of-signal-handler
        """
        exit_fn(signum)

    # start decoder process
    logger.info("Starting decoder process...")
    decoder_process = multiprocessing.Process(
        target=decoder.Decoder.init_and_run,
        args=(child_side, logger, UNLOAD_MODEL_AFTER_S, USE_GPU_IF_AVAILABLE, MAX_MODEL),
        name="Decoder-Process",
        daemon=True,
    )
    decoder_process.start()
    logger.info("Decoder process stared")

    # register handlers that signal decoder process to stop
    signal.signal(signal.SIGINT, signal_worker_to_exit)  # Handle Control + C
    signal.signal(signal.SIGTERM, signal_worker_to_exit)  # Handle 'kill' command
    signal.signal(signal.SIGHUP, signal_worker_to_exit)  # Handle terminal closure

    # start thread to listen to decoder process pipe
    decoder_process_listen_thread = threading.Thread(
        target=listen_to_decoder, args=(parent_side, exit_fn), name="Decoder-Listen-Thread", daemon=True
    )
    decoder_process_listen_thread.start()
    logger.info("Listener for decoder process started")
    logger.info("Startup ")

    return exit_fn


@asynccontextmanager
async def lifespan(_app: FastAPI):
    exit_fn = setup_decoder_process_and_listener_thread()
    yield
    exit_fn(signal.SIGTERM)  # just larping as a kill signal


"""
Init API
"""
if IS_MAIN_PROCESS:
    app = FastAPI(
        title="Whisper API",
        description=description,
        version=__version__,
        lifespan=lifespan,
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

    api_end_points = EndPoints(app, task_dict, decoder_state, open_audio_files_dict, parent_side)
    frontend = Frontend(app)

    # credit: https://philstories.medium.com/fastapi-logging-f6237b84ea64
    @app.middleware("http")
    async def log_requests(req: Request, call_next):
        """
        Requests paths/ parameters and response codes/ times.
        Not logging any data from the request/ response body, as it might contain sensitive data.
        """

        idem = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        req_base_str = f'"{req.method} {req.url.path}", rid={idem}'
        origin = f"{req.client.host}:{req.client.port}"

        # logger.info(f'{req_base_str}, q_params={req.query_params or dict()}')
        start_time = time.time()

        resp: Response = await call_next(req)

        process_time = (time.time() - start_time) * 1000

        # build query parameter string
        query_params = ""
        if req.query_params:
            query_params = "?" + "&".join(
                f"{k}={v if k != 'task_id' else uuid_log_format(v)}" for k, v in req.query_params.items()
            )

        logger.info(
            f'{origin} - "{req.method} {req.url.path}{query_params} HTTP/{req.scope['http_version']}" '
            f"{resp.status_code}, completed in: {process_time:.2f}ms"
        )

        return resp


"""
Hook for uvicorn
"""


def start():
    import uvicorn

    # TODO:
    # forwarded_allow_ips= should be set via env var
    # proxy_headers=True only when needed
    uvicorn.run(app, host=API_LISTEN, port=API_PORT, proxy_headers=True, forwarded_allow_ips="*", log_level="warning")


if __name__ == "__main__":
    start()
