import os

API_PORT = int(os.getenv("PORT", 3001))
API_LISTEN = os.getenv("LISTEN", "127.0.0.1")
LOAD_MODEL_ON_STARTUP = int(os.getenv("LOAD_MODEL_ON_STARTUP", 1))
DEVELOP_MODE = int(os.getenv("DEVELOP_MODE", 0))
# None means no timeout
if (UNLOAD_MODEL_AFTER_S := os.getenv("UNLOAD_MODEL_AFTER_S", None)) is not None:
    UNLOAD_MODEL_AFTER_S = int(UNLOAD_MODEL_AFTER_S)
