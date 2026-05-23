from urllib.parse import quote_plus, urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.utils.exceptions import ConfigurationException

_engine_cache = {}

SUPPORTED_DATABASE_TYPES = {"sqlite", "postgresql", "mysql", "mssql"}


def validate_connection_string(conn_str: str) -> None:
    scheme = urlsplit(conn_str).scheme
    if scheme not in settings.ALLOWED_DB_SCHEMES:
        raise ConfigurationException(f"Database scheme '{scheme}' is not allowed")


def build_connection_string(
    db_type: str,
    database_name: str,
    host: str | None = None,
    port: str | None = None,
    username: str | None = None,
    password: str | None = None,
    sqlite_path: str | None = None,
) -> str:
    normalized_type = (db_type or "").strip().lower()
    if normalized_type not in SUPPORTED_DATABASE_TYPES:
        raise ConfigurationException(f"Database type '{db_type}' is not supported")

    if normalized_type == "sqlite":
        path_value = (sqlite_path or database_name or "").strip()
        if not path_value:
            raise ConfigurationException("SQLite requires a database file path")
        normalized_path = path_value.replace("\\", "/")
        if normalized_path.startswith("/"):
            return f"sqlite:///{normalized_path}"
        return f"sqlite:///{normalized_path}"

    if not host or not str(host).strip():
        raise ConfigurationException(f"{normalized_type} requires a host")
    if not database_name or not database_name.strip():
        raise ConfigurationException(f"{normalized_type} requires a database name")
    if not username or not username.strip():
        raise ConfigurationException(f"{normalized_type} requires a username")

    safe_username = quote_plus(username.strip())
    safe_password = quote_plus((password or "").strip())
    safe_host = str(host).strip()
    safe_database = database_name.strip()
    port_segment = f":{str(port).strip()}" if port and str(port).strip() else ""

    if normalized_type == "postgresql":
        return f"postgresql+psycopg2://{safe_username}:{safe_password}@{safe_host}{port_segment}/{safe_database}"
    if normalized_type == "mysql":
        return f"mysql+pymysql://{safe_username}:{safe_password}@{safe_host}{port_segment}/{safe_database}"
    return f"mssql+pyodbc://{safe_username}:{safe_password}@{safe_host}{port_segment}/{safe_database}?driver=ODBC+Driver+17+for+SQL+Server"


def get_engine(conn_str: str):
    validate_connection_string(conn_str)
    if conn_str not in _engine_cache:
        connect_args = {"check_same_thread": False} if conn_str.startswith("sqlite") else {}
        _engine_cache[conn_str] = create_engine(
            conn_str,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
    return _engine_cache[conn_str]


def get_session(conn_str: str):
    engine = get_engine(conn_str)
    return sessionmaker(bind=engine, future=True)()
