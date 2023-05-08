import os

API_PORT = int(os.getenv("PORT", 3001))
API_LISTEN = os.getenv("LISTEN", "127.0.0.1")
LOAD_MODEL_ON_STARTUP = int(os.getenv("LOAD_MODEL_ON_STARTUP", 1))
DEVELOP_MODE = int(os.getenv("DEVELOP_MODE", 0))
# None means no timeout
# when env is not None we reset the value to the converted number, else it stays None
if (UNLOAD_MODEL_AFTER_S := os.getenv("UNLOAD_MODEL_AFTER_S", None)) is not None:
    UNLOAD_MODEL_AFTER_S = int(UNLOAD_MODEL_AFTER_S)

DELETE_RESULTS_AFTER_M = int(os.getenv("DELETE_RESULTS_AFTER_M", 60))
REFRESH_EXPIRATION_TIME_ON_USAGE = int(os.getenv("REFRESH_EXPIRATION_TIME_ON_USAGE", 1))
RUN_RESULT_EXPIRY_CHECK_M = os.getenv("RUN_RESULT_EXPIRY_CHECK_M", 5)
USE_GPU_IF_AVAILABLE = int(os.getenv("USE_GPU_IF_AVAILABLE", 1))
MAX_MODEL = os.getenv("MAX_MODEL", None)
