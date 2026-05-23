from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func

from app.db.metadata import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    status = Column(String, default="queued", nullable=False)
    db_connection = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    profile_name = Column(String, nullable=True)
    model_definitions = Column(JSON, nullable=False)
    sheet_mapping = Column(JSON, nullable=True)
    file_hash = Column(String, nullable=True)
    model_hash = Column(String, nullable=True)
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    success_rows = Column(Integer, default=0, nullable=False)
    failed_rows = Column(Integer, default=0, nullable=False)
    error_file_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
