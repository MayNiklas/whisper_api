import uvicorn

from .main import app


def start():
    """
    Start the webserver.
    Run the app with:
    uvicorn main:app --reload --host 127.0.0.1 --port 8081
    """

    uvicorn.run(app, host="127.0.0.1", port=8081)
