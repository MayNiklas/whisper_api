"""
This file is used to add the src directory to the python path so that the tests can import the modules from the src directory.
"""

import os
import sys

if "src" not in sys.path and "whisper_api" not in sys.modules:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(os.path.abspath(__file__)))) + "/src")
