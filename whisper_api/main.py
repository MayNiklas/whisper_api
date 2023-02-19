from fastapi import FastAPI, File

app = FastAPI()

DEFAULT_MODEL = "large-v2"


@app.post("/v1/transcribe")
async def transcribe(file: bytes = File()):
    """
    Transcribe audio file.
    :param file: Uploaded audio file.
    :return: Transcription of audio file.
    """

    # test via:
    # curl --location --request POST 127.0.0.1:8081/v1/transcribe -F "file=@audio.m4a"
    return {"file_size": len(file)}
