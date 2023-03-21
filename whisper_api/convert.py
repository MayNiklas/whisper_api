from . import model_holder


def transcribe(file, file_language=None) -> str:
    """
    Transcribe a file using the loaded model.

    Args:
        file (str): path to the file

    Returns:
        str: transcribed text
    """

    model = model_holder.get_model()

    # transcribe the file
    transcription = model.transcribe(file, language=file_language)

    return transcription
