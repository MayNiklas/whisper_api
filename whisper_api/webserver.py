import uvicorn

from .main import app


def start():
    """
    Start the webserver.
    Run the app with:

    uvicorn whisper_api:app --reload --host 127.0.0.1 --port 3001

    access docs:
    http://127.0.0.1:3001/docs
    http://127.0.0.1:3001/redoc
    """

    uvicorn.run(app, host="127.0.0.1", port=3001)
