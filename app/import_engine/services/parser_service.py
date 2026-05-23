from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.utils.chunking import chunk_dataframe
from app.utils.exceptions import ValidationException

SOURCE_ROW_FIELD = "__source_row__"
SOURCE_SHEET_FIELD = "__source_sheet__"
ERROR_COLUMN_NAME = "Error"


def _drop_helper_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns_to_drop = [column for column in df.columns if str(column).strip().lower() == ERROR_COLUMN_NAME.lower()]
    if not columns_to_drop:
        return df
    return df.drop(columns=columns_to_drop)


def _attach_source_metadata(df: pd.DataFrame, sheet_name: str, start_row: int) -> pd.DataFrame:
    with_metadata = df.copy()
    with_metadata[SOURCE_ROW_FIELD] = range(start_row, start_row + len(with_metadata))
    with_metadata[SOURCE_SHEET_FIELD] = sheet_name
    return with_metadata


def parse_file(path: str, chunk_size: int | None = None):
    file_path = Path(path)
    extension = file_path.suffix.lower()
    if extension not in settings.ALLOWED_FILE_EXTENSIONS:
        raise ValidationException(f"Unsupported file type '{extension}'")

    effective_chunk_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
    rows_seen = 0

    if extension == ".csv":
        next_row_number = 2
        for chunk in pd.read_csv(file_path, chunksize=effective_chunk_size):
            chunk = chunk.dropna(how="all")
            if chunk.empty:
                continue
            chunk = _drop_helper_columns(chunk)
            chunk = _attach_source_metadata(chunk, "csv", next_row_number)
            next_row_number += len(chunk)
            rows_seen += len(chunk)
            if rows_seen > settings.MAX_ROWS_PER_FILE:
                raise ValidationException("File exceeds the configured maximum row count")
            yield "csv", chunk
        return

    xls = pd.ExcelFile(file_path)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df = df.dropna(how="all")
        if df.empty:
            continue
        df = _drop_helper_columns(df)
        next_row_number = 2
        for chunk in chunk_dataframe(df, effective_chunk_size):
            chunk = _attach_source_metadata(chunk, sheet, next_row_number)
            next_row_number += len(chunk)
            rows_seen += len(chunk)
            if rows_seen > settings.MAX_ROWS_PER_FILE:
                raise ValidationException("File exceeds the configured maximum row count")
            yield sheet, chunk
