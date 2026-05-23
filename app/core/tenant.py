from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass
class TenantContext:
    tenant_id: str


async def require_tenant_context(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> TenantContext | None:
    if not x_tenant_id:
        return None
    if len(x_tenant_id) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant header is too long")
    return TenantContext(tenant_id=x_tenant_id)
