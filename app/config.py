import os
from dotenv import load_dotenv

# Charge le .env à la racine du projet en exécution locale.
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "langgraph-arq-demo")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatbot:local_dev_password@localhost:5432/chatbot",
)

ARQ_QUEUE_NAME = os.getenv("ARQ_QUEUE_NAME", "arq:queue")
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "300"))
MAX_WORKER_JOBS = int(os.getenv("MAX_WORKER_JOBS", "5"))
