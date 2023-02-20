import uuid
from datetime import datetime
from tempfile import NamedTemporaryFile

from . import convert


class Task:
    """
    A task submitted to the API.

    Attributes:
        uuid: A unique identifier for the task.
        time_uploaded: The time the task was uploaded.
        audiofile: The audio file to be processed.
        status: The status of the task.
        time_processing: The time the task started processing.
        time_finished: The time the task finished processing.
        compute_time: The time it took to process the task.
        result: The result of the task.
    """

    def __init__(self):
        self.uuid = uuid.uuid4()
        self.time_uploaded = datetime.now()
        self.audiofile = NamedTemporaryFile()
        self.status = "pending"
        self.time_processing = None
        self.time_finished = None
        self.compute_time = None
        self.result = None

    def __repr__(self):
        return f"Task(uuid={self.uuid}, time_uploaded={self.time_uploaded}, status={self.status})"

    def process(self):
        """
        Process the task.
        """
        # set status to processing
        self.time_processing = datetime.now()
        self.status = "processing"

        # process audio file
        self.result = convert.transcribe(self.audiofile.name)

        # set status to done
        self.time_finished = datetime.now()
        self.compute_time = self.time_finished - self.time_processing
        self.status = "done"

        # delete audio file
        self.audiofile.close()
