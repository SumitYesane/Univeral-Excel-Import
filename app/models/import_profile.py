from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, UniqueConstraint, func

from app.db.metadata import Base


class ImportProfile(Base):
    __tablename__ = "import_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_import_profiles_tenant_name"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    filename_contains = Column(JSON, nullable=True)
    required_headers = Column(JSON, nullable=True)
    sheet_mapping = Column(JSON, nullable=True)
    model_definitions = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
