from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.security import require_api_key
from app.core.tenant import TenantContext, require_tenant_context
from app.import_engine.schema.schema_models import ImportProfileListResponse, ImportProfileResponse, JobListResponse, JobStatusResponse
from app.import_engine.services.profile_service import ImportProfileService
from app.import_engine.services.job_tracker import JobTracker

router = APIRouter(tags=["jobs"], dependencies=[Depends(require_api_key)])


@router.get("/import/status/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, tenant_context: TenantContext | None = Depends(require_tenant_context)):
    job = JobTracker().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if tenant_context and tenant_context.tenant_id != job.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant header does not match job tenant")
    return JobStatusResponse.from_job(job)


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    tenant_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_context: TenantContext | None = Depends(require_tenant_context),
):
    effective_tenant = tenant_context.tenant_id if tenant_context else tenant_id
    jobs = JobTracker().list_jobs(tenant_id=effective_tenant, limit=limit)
    return JobListResponse(jobs=[JobStatusResponse.from_job(job) for job in jobs])


@router.get("/profiles/{tenant_id}", response_model=ImportProfileListResponse)
def list_import_profiles(tenant_id: str, tenant_context: TenantContext | None = Depends(require_tenant_context)):
    if tenant_context and tenant_context.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant header does not match requested tenant")
    profiles = ImportProfileService().list_profiles(tenant_id)
    return ImportProfileListResponse(profiles=[ImportProfileResponse.from_profile(profile) for profile in profiles])


@router.get("/import/errors/{job_id}")
def download_error_file(job_id: str, tenant_context: TenantContext | None = Depends(require_tenant_context)):
    job = JobTracker().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if tenant_context and tenant_context.tenant_id != job.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant header does not match job tenant")
    if not job.error_file_url:
        raise HTTPException(status_code=404, detail="Error artifact not available")

    file_path = Path(job.error_file_url).resolve()
    error_root = settings.ERROR_ROOT.resolve()
    if error_root not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid error artifact path")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Error artifact file not found")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=file_path.name,
    )
