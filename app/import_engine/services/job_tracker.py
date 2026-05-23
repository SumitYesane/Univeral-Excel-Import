import uuid
from contextlib import suppress
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.db.metadata import Base
from app.db.session import _engine, get_job_db
from app.models.import_job import ImportJob
from app.models.import_profile import ImportProfile
from app.utils.file_hash import hash_models


def _model_dump(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


class JobTracker:
    def init_db(self):
        Base.metadata.create_all(bind=_engine)
        self._ensure_compatible_schema()

    def _ensure_compatible_schema(self):
        inspector = inspect(_engine)
        if "import_jobs" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("import_jobs")}
        ddl_by_column = {
            "original_filename": "ALTER TABLE import_jobs ADD COLUMN original_filename VARCHAR",
            "profile_name": "ALTER TABLE import_jobs ADD COLUMN profile_name VARCHAR",
            "error_message": "ALTER TABLE import_jobs ADD COLUMN error_message TEXT",
            "created_at": "ALTER TABLE import_jobs ADD COLUMN created_at DATETIME",
            "updated_at": "ALTER TABLE import_jobs ADD COLUMN updated_at DATETIME",
            "started_at": "ALTER TABLE import_jobs ADD COLUMN started_at DATETIME",
            "completed_at": "ALTER TABLE import_jobs ADD COLUMN completed_at DATETIME",
        }
        with _engine.begin() as conn:
            for column_name, ddl in ddl_by_column.items():
                if column_name not in existing_columns:
                    conn.execute(text(ddl))
            now = datetime.now(timezone.utc)
            with suppress(Exception):
                conn.execute(
                    text(
                        "UPDATE import_jobs SET created_at = COALESCE(created_at, :now), "
                        "updated_at = COALESCE(updated_at, :now)"
                    ),
                    {"now": now},
                )

    def create_job(self, payload):
        db = get_job_db()
        try:
            model_payload = [_model_dump(m) for m in payload.model_definitions]
            job = ImportJob(
                job_id=payload.import_job_id or str(uuid.uuid4()),
                tenant_id=payload.tenant_id,
                status="queued",
                db_connection=payload.db_connection,
                file_url=payload.file_url,
                original_filename=getattr(payload, "original_filename", None),
                profile_name=getattr(payload, "profile_name", None),
                model_definitions=model_payload,
                sheet_mapping=payload.sheet_mapping,
                file_hash=payload.file_hash,
                model_hash=hash_models(model_payload),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return job
        finally:
            db.close()

    def get_job(self, job_id):
        db = get_job_db()
        try:
            return db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
        finally:
            db.close()

    def list_jobs(self, tenant_id: str | None = None, limit: int = 50):
        db = get_job_db()
        try:
            query = db.query(ImportJob).order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            if tenant_id:
                query = query.filter(ImportJob.tenant_id == tenant_id)
            return query.limit(limit).all()
        finally:
            db.close()

    def update_status(self, job_id, status, error_message: str | None = None):
        db = get_job_db()
        try:
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if job:
                job.status = status
                job.error_message = error_message
                if status == "running" and not job.started_at:
                    job.started_at = datetime.now(timezone.utc)
                if status in {"completed", "failed"}:
                    job.completed_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    def update_progress(self, job_id, total, success, failed):
        db = get_job_db()
        try:
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if job:
                job.total_rows = total
                job.processed_rows = success + failed
                job.success_rows = success
                job.failed_rows = failed
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    def complete_job(self, job_id, total, success, failed, error_url):
        db = get_job_db()
        try:
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if job:
                job.status = "completed"
                job.total_rows = total
                job.processed_rows = success + failed
                job.success_rows = success
                job.failed_rows = failed
                job.error_file_url = error_url
                job.error_message = None
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    def is_duplicate_job(self, payload):
        if not payload.file_hash:
            return False
        db = get_job_db()
        try:
            model_hash = hash_models([_model_dump(m) for m in payload.model_definitions])
            existing = (
                db.query(ImportJob)
                .filter(
                    ImportJob.tenant_id == payload.tenant_id,
                    ImportJob.file_hash == payload.file_hash,
                    ImportJob.model_hash == model_hash,
                    ImportJob.status.in_(["queued", "running", "completed"]),
                )
                .first()
            )
            return existing is not None
        finally:
            db.close()
