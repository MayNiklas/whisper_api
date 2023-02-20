from . import model_loader

# load model fitting the hardware we are running on
model = model_loader.load_model()


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
