import redis
from contextlib import contextmanager
from app.core.config import settings


@contextmanager
def acquire_lock(lock_key: str, timeout: int = 60):
    if not settings.REDIS_URL:
        yield True
        return
    client = redis.Redis.from_url(settings.REDIS_URL)
    lock = client.lock(lock_key, timeout=timeout)
    acquired = lock.acquire(blocking=True)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()