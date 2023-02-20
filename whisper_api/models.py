import uuid

class Task:
    """
    A task submitted to the API.

    Attributes:
        uuid: A unique identifier for the task.
    """

    def __init__(self):
        self.uuid = uuid.uuid4()



if __name__ == "__main__":
    task = Task()
    print(task.uuid)
