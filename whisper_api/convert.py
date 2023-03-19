import gc
import os

import torch

from . import model_loader

# preload bool default to False
# if set to True, the model will be loaded at startup
# if set to False, the model will be loaded on the fly
# -> when set to True, it will perform way faster but will use vRAM continuously
# -> when set to False, it will use vRAM only when transcribing a file, but needs to load the model each time
preload = os.environ.get("PRELOAD", "False").lower() == "true"

if preload:
    # load model fitting the hardware we are running on
    print("Preload is set, loading model...")
    global model
    model = model_loader.load_model()


def transcribe(file, file_language=None) -> str:
    """
    Transcribe a file using the loaded model.

    Args:
        file (str): path to the file

    Returns:
        str: transcribed text
    """

    if preload:
        # use global preloaded model
        global model

    else:
        # load model fitting the hardware we are running on
        print("Preload is not set, loading model on the fly...")
        model = model_loader.load_model()

    # transcribe the file
    transcription = model.transcribe(file, language=file_language)

    if not preload:
        # free vRAM
        del model
        gc.collect()
        torch.cuda.empty_cache()

    return transcription
