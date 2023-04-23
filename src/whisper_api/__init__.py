import multiprocessing
import os
import sys

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

if __package__ is None and not hasattr(sys, "frozen"):
    import os.path

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))


from whisper_api.environment import API_PORT, API_LISTEN
from whisper_api.version import __version__

description = """
Whisper API transcribes audio files.
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

# create Pipe for communication between main and worker thread
conn_to_parent, conn_to_child = multiprocessing.Pipe(duplex=True)

def start():
    import uvicorn

    uvicorn.run(app, host=API_LISTEN, port=API_PORT)
