import threading
from app.core.config import settings


_tenant_semaphores = {}


def get_semaphore(tenant_id: str) -> threading.BoundedSemaphore:
    if tenant_id not in _tenant_semaphores:
        _tenant_semaphores[tenant_id] = threading.BoundedSemaphore(settings.MAX_CONCURRENT_IMPORTS_PER_TENANT)
    return _tenant_semaphores[tenant_id]
