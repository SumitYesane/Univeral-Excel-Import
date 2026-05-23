import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _split_csv_env(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    ENV: str = os.getenv("ENV", "dev")
    APP_NAME: str = os.getenv("APP_NAME", "Universal Import Service")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
    JOB_DB_URL: str = os.getenv("JOB_DB_URL", "sqlite:///./import_jobs.db")
    STORAGE_ROOT: Path = Path(os.getenv("STORAGE_ROOT", "./storage")).resolve()
    ERROR_ROOT: Path = Path(os.getenv("ERROR_ROOT", "./errors")).resolve()
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    USE_CELERY: bool = os.getenv("USE_CELERY", "false").lower() == "true"
    MAX_CONCURRENT_IMPORTS_PER_TENANT: int = int(os.getenv("MAX_CONCURRENT_IMPORTS_PER_TENANT", "3"))
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "2000"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    MAX_ERRORS_PER_JOB: int = int(os.getenv("MAX_ERRORS_PER_JOB", "5000"))
    MAX_ROWS_PER_FILE: int = int(os.getenv("MAX_ROWS_PER_FILE", "100000"))
    ALLOWED_FILE_EXTENSIONS: List[str] = field(
        default_factory=lambda: _split_csv_env(os.getenv("ALLOWED_FILE_EXTENSIONS", ".csv,.xlsx,.xls"))
    )
    ALLOWED_DB_SCHEMES: List[str] = field(
        default_factory=lambda: _split_csv_env(
            os.getenv("ALLOWED_DB_SCHEMES", "sqlite,postgresql,postgresql+psycopg2,mysql,mysql+pymysql,mssql+pyodbc")
        )
    )
    API_KEYS: List[str] = field(default_factory=lambda: _split_csv_env(os.getenv("API_KEYS", "")))
    ALLOWED_ORIGINS: List[str] = field(default_factory=lambda: _split_csv_env(os.getenv("ALLOWED_ORIGINS", "*")))

    @property
    def auth_enabled(self) -> bool:
        return bool(self.API_KEYS)


settings = Settings()
