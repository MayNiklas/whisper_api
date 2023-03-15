import argparse
import time

import requests

url = "http://10.7.0.200:3001/"


def upload_audio_file(file: str):
    """
    Uploads an audio file to the server.
    :param file: The file to upload.
    :return: The response from the server.
    """
    files = {"file": open(file, "rb")}

    return requests.post(url + "v1/transcribe", files=files).json()["task_id"]


def get_status(id: str):
    """
    Get the status of a transcription.
    :param id: The ID of the transcription.
    :return: The status of the transcription.
    """
    return requests.get(url + "v1/status/" + id).json()["status"]


def get_text(id: str):
    """
    Get the transcription.
    :param id: The ID of the transcription.
    :return: The text of the transcription.
    """
    return requests.get(url + "v1/status/" + id).json()["transcript"]


def cli():
    """
    Transcribe an audio file from CLI.
    """

    parser = argparse.ArgumentParser(description="Transcribe an audio file.")
    parser.add_argument("file", help="The file to transcribe.")
    args = parser.parse_args()
    file = args.file

    id = upload_audio_file(file)

    while get_status(id) != "done":
        time.sleep(0.25)

    print(get_text(id))
