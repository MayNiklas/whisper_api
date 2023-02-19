from .model_loader import load_model

# load model fitting the hardware we are running on
model = load_model()


def get_length(result) -> float:
    """
    Get the length of a segment in seconds.

    Args:
        result (dict): result of the transcribe function

    Returns:
        str: length in seconds
    """

    # placeholder:
    # for some reason, this does not result in the correct length of the file
    # it's always a bit too long (seems like 0-7 seconds too long?)

    first_segment = result["segments"][0]
    last_segment = result["segments"][-1]

    return last_segment["end"] - first_segment["start"]


def transcribe(file) -> str:
    """
    Transcribe a file using the loaded model.

    Args:
        file (str): path to the file

    Returns:
        str: transcribed text
    """

    # transcribe the file
    return model.transcribe(file)
