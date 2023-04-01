import uuid
from datetime import datetime
from tempfile import NamedTemporaryFile


class Task:
    """
    A task submitted to the API.

    Attributes:
        uuid: A unique identifier for the task.
        time_uploaded: The time the task was uploaded.
        audiofile: The audio file to be processed.
        status: The status of the task.
        result: The result of the task.
    """

    def __init__(self):
        self.uuid = uuid.uuid4()
        self.time_uploaded = datetime.now()
        self.audiofile = NamedTemporaryFile()
        self.srt = NamedTemporaryFile(mode="w", suffix=".srt")
        self.language = None
        self.status = "pending"
        self.result = None

    def __repr__(self):
        return f"Task(uuid={self.uuid}, time_uploaded={self.time_uploaded}, status={self.status})"


# List holding tasks - TODO: this is very temporary!
tasks = []
