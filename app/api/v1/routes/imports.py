from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.security import require_api_key
from app.core.tenant import TenantContext, require_tenant_context
from app.db.connection import build_connection_string, validate_connection_string
from app.import_engine.pipeline import run_import_job
from app.import_engine.schema.schema_models import ImportRequest, ImportResponse
from app.import_engine.services.profile_service import ImportProfileService
from app.import_engine.services.job_tracker import JobTracker
from app.import_engine.services.storage_service import StorageService
from app.utils.exceptions import ConfigurationException, StorageException
from app.utils.file_hash import compute_file_hash
from app.workers.tasks import process_import

router = APIRouter(tags=["imports"], dependencies=[Depends(require_api_key)])


def _validate_tenant_scope(payload_tenant: str, tenant_context: TenantContext | None) -> None:
    if tenant_context and tenant_context.tenant_id != payload_tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant header does not match payload tenant")


def _resolve_db_connection(
    db_connection: str | None,
    db_type: str | None,
    database_name: str | None,
    host: str | None,
    port: str | None,
    username: str | None,
    password: str | None,
    sqlite_path: str | None,
) -> str:
    if db_connection and db_connection.strip():
        validate_connection_string(db_connection.strip())
        return db_connection.strip()

    connection = build_connection_string(
        db_type=db_type or "",
        database_name=database_name or "",
        host=host,
        port=port,
        username=username,
        password=password,
        sqlite_path=sqlite_path,
    )
    validate_connection_string(connection)
    return connection


@router.post("/imports", response_model=ImportResponse, status_code=status.HTTP_202_ACCEPTED)
def create_import_job(
    payload: ImportRequest,
    background_tasks: BackgroundTasks,
    tenant_context: TenantContext | None = Depends(require_tenant_context),
):
    _validate_tenant_scope(payload.tenant_id, tenant_context)
    try:
        validate_connection_string(payload.db_connection)
    except ConfigurationException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    job_tracker = JobTracker()

    if job_tracker.is_duplicate_job(payload):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate import detected")

    job = job_tracker.create_job(payload)

    if settings.USE_CELERY:
        process_import.delay(job.job_id)
    else:
        background_tasks.add_task(run_import_job, job.job_id)

    return ImportResponse.from_job(job)


@router.post("/imports/upload", response_model=ImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_create_job(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    db_connection: str | None = Form(default=None),
    db_type: str = Form(default="sqlite"),
    database_name: str | None = Form(default=None),
    host: str | None = Form(default=None),
    port: str | None = Form(default=None),
    username: str | None = Form(default=None),
    password: str | None = Form(default=None),
    sqlite_path: str | None = Form(default=None),
    file: UploadFile = File(...),
    tenant_context: TenantContext | None = Depends(require_tenant_context),
):
    _validate_tenant_scope(tenant_id, tenant_context)
    storage = StorageService()
    try:
        stored_path = await storage.save_upload(file, tenant_id)
    except StorageException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_hash = compute_file_hash(stored_path)
    profile_service = ImportProfileService()

    try:
        resolved_db_connection = _resolve_db_connection(
            db_connection=db_connection,
            db_type=db_type,
            database_name=database_name,
            host=host,
            port=port,
            username=username,
            password=password,
            sqlite_path=sqlite_path,
        )
        request_components = profile_service.build_request_components(tenant_id, stored_path, original_filename=file.filename)
        payload = ImportRequest(
            tenant_id=tenant_id,
            db_connection=resolved_db_connection,
            file_url=stored_path,
            model_definitions=request_components["model_definitions"],
            sheet_mapping=request_components["sheet_mapping"],
            file_hash=file_hash,
            original_filename=file.filename,
            profile_name=request_components["profile"].name,
        )
    except (ValueError, ConfigurationException) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    job_tracker = JobTracker()
    if job_tracker.is_duplicate_job(payload):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate import detected")

    job = job_tracker.create_job(payload)

    if settings.USE_CELERY:
        process_import.delay(job.job_id)
    else:
        background_tasks.add_task(run_import_job, job.job_id)

    return ImportResponse.from_job(job)
