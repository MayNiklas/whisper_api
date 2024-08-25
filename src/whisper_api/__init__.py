import os
import sys

if __package__ is None and not hasattr(sys, "frozen"):

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

from whisper_api.log_setup import logger
from whisper_api.main import start, app

start()
