from tempfile import NamedTemporaryFile

from fastapi import FastAPI, UploadFile

from .convert import transcribe as convert

app = FastAPI()

DEFAULT_MODEL = "large-v2"


@app.post("/v1/transcribe")
async def transcribe(file: UploadFile):
    """
    Transcribe audio file.
    :param file: Uploaded audio file.
    :return: Transcription of audio file.
    """

    # save file to temporary file
    temp = NamedTemporaryFile()
    temp.write(await file.read())

    result = convert(temp.name)

    # test via:
    # curl --location --request POST 127.0.0.1:8081/v1/transcribe -F "file=@audio.m4a"

    return {
        "filename": file.filename,
        "language": result["language"],
        "transcript": result["text"],
    }
