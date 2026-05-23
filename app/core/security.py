from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str | None:
    if not settings.auth_enabled:
        return None
    if x_api_key in settings.API_KEYS:
        return x_api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )
