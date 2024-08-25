import argparse
import os
import threading

import whisper

download_root = os.path.join(
    os.getenv("XDG_CACHE_HOME", os.path.join(os.path.expanduser("~"), ".cache")),
    "whisper",
)


def download_model(name: str):
    """
    Download the whisper ASR model.

    Args:
        name: The name of the model to download.
    """

    if name in whisper._MODELS:
        whisper._download(whisper._MODELS[name], download_root, in_memory=False)

    else:
        raise RuntimeError(f"Model {name} not found; available models = {whisper.available_models()}")


if __name__ == "__main__":
    """
    Download models in advance.
    """

    parser = argparse.ArgumentParser(description="Download a Whisper ASR model.")
    parser.add_argument("--model", type=str, default="all", help="The name of the model to download.")

    args = parser.parse_args()

    if args.model != "all":
        print(f"Pre fetching whisper model {args.model}...")
        download_model(args.model)
        exit(0)

    else:
        print("Pre fetching all whisper models...")

        models = ["large", "medium", "base", "small", "tiny"]

        threads = []

        for model in models:
            threads.append(threading.Thread(target=download_model, args=(model,)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
