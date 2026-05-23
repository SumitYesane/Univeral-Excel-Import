from sqlalchemy import MetaData, Table

from app.db.connection import get_session


def bulk_insert_rows(conn_str, table_name, rows):
    if not rows:
        return 0
    session = get_session(conn_str)
    try:
        meta = MetaData()
        table = Table(table_name, meta, autoload_with=session.bind)
        allowed_columns = {column.name for column in table.columns}
        sanitized_rows = [{key: value for key, value in row.items() if key in allowed_columns} for row in rows]
        session.execute(table.insert(), sanitized_rows)
        session.commit()
        return len(sanitized_rows)
    finally:
        session.close()
