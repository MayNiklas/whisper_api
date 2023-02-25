from os import getenv

import torch
import whisper

dev_mode = getenv("DEV_MODE", False)


def get_fitting_model() -> str:
    """
    Get the name of the model that fits the available GPU memory.

    Returns:
        str: name of the model
    """

    if dev_mode:
        print("DEV_MODE is set, using model small...")
        return "small"

    # check if GPU is available
    if torch.cuda.is_available():
        print("GPU available, using GPU...")

        # depending on the vRAM size, we can use a different model
        vram_model_map = {
            "large": 10,
            "medium": 5,
            "small": 2,
            "base": 1,
        }

        # find the best model for the available/free VRAM
        for model_name, vram_size in vram_model_map.items():
            if torch.cuda.mem_get_info()[0] >= vram_size * 1e9:
                print(f"Using model {model_name}...")
                return model_name

        # TODO: we should force using the CPU,
        # if no model fits the available VRAM

    else:
        print("GPU not available, using CPU...")
        # since the CPU is much slower,
        # I suggest using the medium model when no GPU is available
        print(f"Using model medium...")
        return "medium"


def load_model() -> whisper.Whisper:
    """
    Load the model fitting the current hardware.

    Returns:
        whisper.Whisper: loaded model
    """

    # TODO: we should add a lot of error handling here
    return whisper.load_model(
        get_fitting_model(),
        in_memory=True,
    )
