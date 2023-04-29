import os

API_PORT = int(os.getenv("PORT", 3001))
API_LISTEN = os.getenv("LISTEN", "127.0.0.1")
KEEP_MODEL_IN_MEMORY = os.getenv("KEEP_MODEL_IN_MEMORY", "True").lower() == "true"
