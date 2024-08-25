import os
import sys

if __package__ is None and not hasattr(sys, "frozen"):

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

from whisper_api.main import start, app

if __name__ == '__main__':
    start()
