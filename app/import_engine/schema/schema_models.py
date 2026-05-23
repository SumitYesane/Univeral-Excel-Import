from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.import_engine.models.model_definitions import ModelDefinition


class ImportRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    import_job_id: Optional[str] = None
    db_connection: str = Field(min_length=1)
    file_url: str = Field(min_length=1)
    model_definitions: List[ModelDefinition]
    sheet_mapping: Optional[Dict[str, List[str]]] = None
    file_hash: Optional[str] = None
    original_filename: Optional[str] = None
    profile_name: Optional[str] = None

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("tenant_id is required")
        return value

    @model_validator(mode="after")
    def validate_sheet_mapping(self):
        if self.sheet_mapping:
            model_names = {model.name for model in self.model_definitions}
            for sheet, names in self.sheet_mapping.items():
                if not names:
                    raise ValueError(f"Sheet '{sheet}' must map to at least one model")
                missing = [name for name in names if name not in model_names]
                if missing:
                    raise ValueError(f"Sheet '{sheet}' references unknown models: {', '.join(missing)}")
        return self

class ImportResponse(BaseModel):
    job_id: str
    status: str
    created_at: Optional[datetime] = None

    @classmethod
    def from_job(cls, job):
        return cls(job_id=job.job_id, status=job.status, created_at=getattr(job, "created_at", None))


class JobStatusResponse(BaseModel):
    job_id: str
    tenant_id: str
    status: str
    total_rows: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    error_file_url: Optional[str]
    error_message: Optional[str]
    original_filename: Optional[str]
    profile_name: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @classmethod
    def from_job(cls, job):
        return cls(
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            status=job.status,
            total_rows=job.total_rows,
            processed_rows=job.processed_rows,
            success_rows=job.success_rows,
            failed_rows=job.failed_rows,
            error_file_url=job.error_file_url,
            error_message=job.error_message,
            original_filename=job.original_filename,
            profile_name=getattr(job, "profile_name", None),
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )


class JobListResponse(BaseModel):
    jobs: List[JobStatusResponse]


class ImportProfileResponse(BaseModel):
    tenant_id: str
    name: str
    description: Optional[str]
    is_default: bool
    filename_contains: List[str] = Field(default_factory=list)
    required_headers: List[str] = Field(default_factory=list)
    sheet_mapping: Optional[Dict[str, List[str]]] = None

    @classmethod
    def from_profile(cls, profile):
        return cls(
            tenant_id=profile.tenant_id,
            name=profile.name,
            description=profile.description,
            is_default=profile.is_default,
            filename_contains=profile.filename_contains or [],
            required_headers=profile.required_headers or [],
            sheet_mapping=profile.sheet_mapping,
        )


class ImportProfileListResponse(BaseModel):
    profiles: List[ImportProfileResponse]
