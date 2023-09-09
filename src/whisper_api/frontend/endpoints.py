import os.path
import sys

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from starlette.responses import FileResponse


# get folder of this file
static_path = os.path.dirname(os.path.realpath(__file__)) + "/static"


class Frontend:
    def __init__(self, app: FastAPI):
        self.app = app

        self.add_endpoints()

    def add_endpoints(self):
        self.app.add_api_route("/{file_path:path}", self.frontend)

    async def frontend(self, file_path: str, request: Request):
        """
        Serve static files e.g. the frontend.
        :param file_path: Path to the file.
        :return: File.
        """

        # this has no effect yet!
        # just trying out if it works as expected!
        if request.headers.get('X-Email'):
            user = {}
            user['user'] = request.headers.get('X-User')
            user['email'] = request.headers.get('X-Email')

        if file_path == "":
            file_path = "index.html"

        allowed_files = ["index.html", "script.js", "styles.css"]

        if file_path not in allowed_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{file_path}' not found.",
            )

        return FileResponse(f"{static_path}/{file_path}")
