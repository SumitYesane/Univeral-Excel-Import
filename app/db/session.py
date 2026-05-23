from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.JOB_DB_URL.startswith("sqlite") else {}
_engine = create_engine(settings.JOB_DB_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=_engine, future=True)


def get_job_db():
    return SessionLocal()
