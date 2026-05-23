from sqlalchemy import MetaData, Table, select

from app.db.connection import get_session
from app.import_engine.services.error_file_service import build_error_entry
from app.import_engine.services.parser_service import SOURCE_ROW_FIELD, SOURCE_SHEET_FIELD


def filter_file_duplicates(df, unique_cols, model_name: str):
    if not unique_cols:
        return df, []
    dupes = df[df.duplicated(subset=unique_cols, keep=False)]
    errors = []
    for idx, row in dupes.iterrows():
        row_dict = row.to_dict()
        errors.append(
            build_error_entry(
                row=row_dict.get(SOURCE_ROW_FIELD, int(idx) + 1),
                sheet=row_dict.get(SOURCE_SHEET_FIELD),
                model_name=model_name,
                data=row_dict,
                error_message="Duplicate in file",
            )
        )
    filtered = df.drop(dupes.index)
    return filtered, errors


def filter_db_duplicates(conn_str, table_name, rows, unique_cols, model_name: str):
    if not unique_cols or not rows:
        return rows, []

    session = get_session(conn_str)
    errors = []
    to_exclude = set()
    try:
        meta = MetaData()
        table = Table(table_name, meta, autoload_with=session.bind)
        for col in unique_cols:
            if col not in table.c:
                continue
            values = [row.get(col) for row in rows if row.get(col) is not None]
            if not values:
                continue
            stmt = select(table.c[col]).where(table.c[col].in_(values))
            result = session.execute(stmt).scalars().all()
            existing = set(result)
            for row in rows:
                if row.get(col) in existing:
                    key = tuple(row.get(c) for c in unique_cols)
                    to_exclude.add(key)
                    errors.append(
                        build_error_entry(
                            row=row.get(SOURCE_ROW_FIELD),
                            sheet=row.get(SOURCE_SHEET_FIELD),
                            model_name=model_name,
                            data=row,
                            error_message=f"Duplicate in DB: {col}",
                        )
                    )

        filtered = [row for row in rows if tuple(row.get(c) for c in unique_cols) not in to_exclude]
        return filtered, errors
    finally:
        session.close()
