import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
REDIS_BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "scholar_tasks",
    broker=REDIS_URL,
    backend=REDIS_BACKEND_URL,
    include=["tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
