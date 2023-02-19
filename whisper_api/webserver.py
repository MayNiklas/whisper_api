import uvicorn

from .main import app


def start():
    """
    Start the webserver.
    Run the app with:

    uvicorn main:app --reload --host 127.0.0.1 --port 8081
    uvicorn whisper_api:app --reload --host 127.0.0.1 --port 8081

    whisper_api

    access docs:
    http://127.0.0.1:8081/docs
    http://127.0.0.1:8081/redoc
    """

    uvicorn.run(app, host="127.0.0.1", port=8081)
