from typing import Optional

from pydantic import BaseModel, create_model


def build_model(name: str, column_types: dict, required_fields: Optional[list] = None):
    required_fields = set(required_fields or [])
    fields = {}
    for field_name, field_type in column_types.items():
        if field_name in required_fields:
            fields[field_name] = (field_type, ...)
        else:
            fields[field_name] = (Optional[field_type], None)
    return create_model(name, __base__=BaseModel, **fields)
