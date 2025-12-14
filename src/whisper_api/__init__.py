import os
import sys

if __package__ is None and not hasattr(sys, "frozen"):

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

__version__ = "20251214"


from whisper_api.main import am_i_main_process
if am_i_main_process():
    from whisper_api.main import app  # isort: skip
    from whisper_api.main import start

if __name__ == "__main__":
    start()
