import multiprocessing
import os
import sys

if __package__ is None and not hasattr(sys, "frozen"):

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

__version__ = "20251214"


from whisper_api.main import am_i_main_process
def start():
    """Mock Version of start() that is overwritten in the main process by the import below."""
    name = multiprocessing.current_process().name
    raise ImportError(f"You're trying to run start() from another process than Main "
                      f"(you are: '{name}'). This is currently not supported.")

if am_i_main_process():
    from whisper_api.main import app  # isort: skip
    from whisper_api.main import start

if __name__ == "__main__":
    start()
