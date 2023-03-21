import gc
import os
from multiprocessing import Pipe

import torch

from . import model_loader


# preload bool default to False
# if set to True, the model will be loaded at startup
# if set to False, the model will be loaded on the fly
# -> when set to True, it will perform way faster but will use vRAM continuously
# -> when set to False, it will use vRAM only when transcribing a file, but needs to load the model each time
preload = os.environ.get("PRELOAD", "False").lower() == "true"

global model

model = None

if preload:
    # load model fitting the hardware we are running on
    print("Preload is set, loading model...")
    model = model_loader.load_model()


def get_model():
    """
    Get the model
    """

    global model

    if model is not None:
        return model
    else:
        model = model_loader.load_model()
        return model


def clean_model(conn: Pipe):
    """
    Clean the model from memory
    """

    global model

    # if preload is disabled
    if not preload:
        # if no task is left in queue
        if not conn.poll(180):
            # clean model from memory
            model = None
            gc.collect()
            torch.cuda.empty_cache()
