import math
import re
from typing import List, Tuple

from pydantic import ValidationError

from app.import_engine.schema.dynamic_pydantic import build_model
from app.import_engine.services.error_file_service import build_error_entry
from app.import_engine.services.parser_service import SOURCE_ROW_FIELD, SOURCE_SHEET_FIELD


def _normalize_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _normalize_row(row_dict: dict) -> dict:
    return {key: _normalize_value(value) for key, value in row_dict.items()}


def validate_rows(df, model_def) -> Tuple[List[dict], List[dict]]:
    valid = []
    errors = []
    required = model_def.required_fields()
    regex_rules = model_def.regex_rules()
    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
    }
    model = None
    column_types = {k: type_map.get(v, str) for k, v in model_def.column_types().items()}
    if column_types:
        model = build_model(f"{model_def.table}_model", column_types, required)

    for idx, row in df.iterrows():
        row_dict = _normalize_row(row.to_dict())
        row_errors = []

        for field in required:
            if row_dict.get(field) in (None, ""):
                row_errors.append(f"{field} is required")

        for field, pattern in regex_rules.items():
            value = row_dict.get(field)
            if value not in (None, "") and not re.match(pattern, str(value)):
                row_errors.append(f"{field} format invalid")

        if model and not row_errors:
            try:
                parsed = model(**row_dict)
                row_dict = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed.dict()
            except ValidationError as ve:
                row_errors.extend([error["msg"] for error in ve.errors()])

        if row_errors:
            errors.append(
                build_error_entry(
                    row=row_dict.get(SOURCE_ROW_FIELD, int(idx) + 1),
                    sheet=row_dict.get(SOURCE_SHEET_FIELD),
                    model_name=model_def.name,
                    data=row_dict,
                    error_message="; ".join(row_errors),
                )
            )
        else:
            valid.append(row_dict)

    return valid, errors
