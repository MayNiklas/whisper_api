import uuid
from tempfile import NamedTemporaryFile


class Task:
    """
    A task submitted to the API.

    Attributes:
        uuid: A unique identifier for the task.
    """

    def __init__(self):
        self.uuid = uuid.uuid4()
        self.audiofile = NamedTemporaryFile()
        self.status = "pending"
        self.result = None
