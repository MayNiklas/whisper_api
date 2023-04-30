import os

API_PORT = int(os.getenv("PORT", 3001))
API_LISTEN = os.getenv("LISTEN", "127.0.0.1")
KEEP_MODEL_IN_MEMORY = os.getenv("KEEP_MODEL_IN_MEMORY", "True").lower() == "true"
DEVELOP_MODE = os.getenv("DEVELOP_MODE", "False").lower() == "true"
# None means no timeout
if (UNLOAD_MODEL_AFTER_S := os.getenv("UNLOAD_MODEL_AFTER_S", None)) is not None:
    UNLOAD_MODEL_AFTER_S = int(UNLOAD_MODEL_AFTER_S)
