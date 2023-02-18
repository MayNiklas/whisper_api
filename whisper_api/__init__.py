import whisper


def _download_models():
    """
    Download all international models Whisper has available.
    """

    for model in whisper.available_models():
        # only load international models
        if model.endswith('.en'):
            continue
        else:
            load_model = whisper.load_model(name=model)
            # unload the model from memory
            del load_model


_download_models()
