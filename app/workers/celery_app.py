from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "import_worker",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
)