import atexit
import logging
import multiprocessing
import os
import threading
from logging.handlers import TimedRotatingFileHandler
from multiprocessing.connection import Connection
from typing import Literal

from whisper_api.data_models.data_types import private_uuid_hex_t
from whisper_api.data_models.data_types import uuid_hex_t
from whisper_api.environment import LOG_DATE_FORMAT
from whisper_api.environment import LOG_FORMAT
from whisper_api.environment import LOG_LEVEL_CONSOLE
from whisper_api.environment import LOG_LEVEL_FILE
from whisper_api.environment import LOG_PRIVACY_MODE
from whisper_api.environment import LOG_ROTATION_BACKUP_COUNT
from whisper_api.environment import LOG_ROTATION_INTERVAL
from whisper_api.environment import LOG_ROTATION_WHEN

# set logging format
formatter_string = LOG_FORMAT
formatter_style: Literal["%", "$", "{"] = "{"
formatter_date_fmt = LOG_DATE_FORMAT
formatter = logging.Formatter(formatter_string, style="{")
# TODO why is this here AND USED? - why? can we just replace it with the normal format??
rich_formatter = logging.Formatter(
    "[{asctime}] [{levelname}] [{threadName}] {message}", style=formatter_style, datefmt=formatter_date_fmt
)

# get new logger
logger = logging.getLogger("logger")
# set logger to lowest level we wanna log anywhere!
# if we don't do this logging will assume WARNING as default
# handlers won't get messages for lower levels, because they're discarded
# why the fuck is this how it's done?! - serious. what a crap...

# register loggers
logger.setLevel(logging.DEBUG)


def uuid_log_format(uid: uuid_hex_t) -> uuid_hex_t | private_uuid_hex_t:
    """
    returns the all task uuids shall be logged as.
    reason: the uuids shall not be visible in a privacy focussed production deployment
    the print of an uuid might allow the host to access the data we try to hide
    """
    if LOG_PRIVACY_MODE:
        return f"<task_uuid: {uid[:4]}...{uid[-4:]}>"
    return uid


# TODO: rotating filehandler?
class PipedFileHandler(TimedRotatingFileHandler):
    """A logger that can be used in two processes, but only writes from MainProcess"""

    def __init__(self, log_pipe: Connection, log_dir: str, log_file: str, **rotating_file_handler_kwargs):
        if log_dir:
            self.log_path = os.path.join(log_dir, log_file)
        else:
            self.log_path = log_file

        super().__init__(self.log_path, **rotating_file_handler_kwargs)
        self.log_pipe = log_pipe

        if multiprocessing.current_process().name == "MainProcess":
            # start listening for logs from children
            self.listener_thread = threading.Thread(target=self.listen_for_logs_from_children, args=(self.log_pipe,))
            self.listener_thread.daemon = True
            self.listener_thread.start()
            atexit.register(self.wait_for_listener)
            self.is_end = False

    @property
    def am_I_main(self):
        return multiprocessing.current_process().name == "MainProcess"

    def wait_for_listener(self):
        """Ensure that we wait for thread when we shall exit"""
        # well, we won't try to use the logger when waiting for logging to be finished :)
        print("Stopping listener for logger...")
        if self.am_I_main:
            self.is_end = True
            print("Waiting for logger to finish writing...")
            self.listener_thread.join()
            print("Logger closed")

    def emit(self, record: logging.LogRecord):
        """Emit the message or send it to the main"""

        # if we're in a child process, send the record to the pipe to main process
        if not self.am_I_main:
            self.log_pipe.send(record)
            return

        # only write from main process
        # we need to replace the process name manually, otherwise processName is overwritten with 'MainProcess'
        if record.processName != "MainProcess":
            _formatter = logging.Formatter(
                formatter_string.replace("{processName}", record.processName),
                style=formatter_style,
                datefmt=formatter_date_fmt,
            )

        # just use the normal formatter for main messages
        else:
            _formatter = logging.Formatter(formatter_string, style=formatter_style, datefmt=formatter_date_fmt)

        self.setFormatter(_formatter)
        super().emit(record)

    def listen_for_logs_from_children(self, pipe_to_listen_to: Connection, wait_before_exit_s: float = 1.0):
        """Tread listening for logs from children and sending them to main process"""
        while True:
            try:
                # time out every few seconds to check if we should come to and end
                if not pipe_to_listen_to.poll(wait_before_exit_s):
                    # as long as logs fly in we will not terminate
                    # we just timed out because nothing was there, if we shall stop, we can sow
                    if self.is_end:
                        break
                    # no, it's not the ending, just go back to loop
                    continue

                # data! yay
                record = pipe_to_listen_to.recv()
                self.emit(record)

            # set exit flag which wil trigger after next timeout
            # and yes. this bare except is chosen by design
            except:
                self.is_end = True


def configure_logging(
    _logger: logging.Logger,
    log_dir: str = "",
    log_file: str = "events.log",
    log_pipe: Connection = None,
    console_logger_level=LOG_LEVEL_CONSOLE,
    file_logger_level=LOG_LEVEL_FILE,
    logger_base_level=logging.DEBUG,
):
    """
    The function to call from the outside to configure the PipedLogger
    Args:
        _logger: The logger to configure
        log_dir: The directory to store the log file in, created if not exists (empty or None for same directory)
        log_file: The name of the log file (default: events.log)
        log_pipe: The pipe to send logs to the main process (if set file-logging will be done using the pipe handler)
        console_logger_level: The level to log to console (None for no console logging)
        file_logger_level: The level to log to file (None for no file logging, even if pipe is set)
        logger_base_level: The base level of the logger (everything below will be discarded, recommended: DEBUG)
    """
    # path for databases or config files
    if log_dir and not os.path.exists(log_dir):
        os.mkdir(log_dir)

    _logger.setLevel(logger_base_level)

    if log_pipe and file_logger_level:
        pipe_logger = PipedFileHandler(
            log_pipe,
            log_dir,
            log_file,
            when=LOG_ROTATION_WHEN,
            interval=LOG_ROTATION_INTERVAL,
            backupCount=LOG_ROTATION_BACKUP_COUNT,
        )
        pipe_logger.setLevel(file_logger_level)
        pipe_logger.setFormatter(rich_formatter)
        _logger.addHandler(pipe_logger)

    elif file_logger_level:
        file_logger = logging.FileHandler(f"{log_dir}/{log_file}" if log_dir else log_file)
        file_logger.setLevel(file_logger_level)
        file_logger.setFormatter(formatter)
        _logger.addHandler(file_logger)

    if console_logger_level:
        # logger for console prints
        console_logger = logging.StreamHandler()
        console_logger.setLevel(console_logger_level)
        console_logger.setFormatter(formatter)
        _logger.addHandler(console_logger)


if __name__ == "__main__":
    # small test
    import logging
    import multiprocessing
    import os
    import time
    from multiprocessing import Pipe
    from multiprocessing import Process

    _log_pipe, _child_pipe = Pipe()

    # Create a temporary file for the log output
    log_file_path = "log_file_dummy.log"
    open(log_file_path, "w").close()

    # Create a logger and add the PipedFileHandler to it
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(PipedFileHandler(_log_pipe, log_file_path))
    configure_logging(logger, "", log_file_path, _log_pipe)

    # Define a function to be run by the child process
    def child_function():
        time.sleep(1.5)
        logger.info("This is a log message from the child process")

    # Spawn a child process and wait for it to finish
    process = Process(target=child_function)
    process.start()

    logger.info("This is a test message")
    process.join()

    time.sleep(2)  # wait for the message to be processed

    # Read the log file and check that the log message from the child process is present
    with open(log_file_path) as _log_file:
        log_contents = _log_file.read()
        assert "This is a log message from the child process" in log_contents

    # Send a log message through the pipe and check that it is present in the log file
    _log_pipe.send(
        logging.LogRecord("test_logger", logging.INFO, "test_logger", 0, "This is a test message", None, None)
    )
    time.sleep(1)  # wait for the message to be processed
    with open(log_file_path) as _log_file:
        log_contents = _log_file.read()
        assert "This is a test message" in log_contents
        print(f"{log_contents=}")

    # Clean up
    # os.remove(log_file_path)
    print("Done")

    exit()
