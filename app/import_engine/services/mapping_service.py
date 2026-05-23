import re


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())


def build_column_mapping(columns, model_def, extra_fields=None):
    normalized_cols = {_normalize(c): c for c in columns}
    mapping = {}
    aliases = model_def.alias_map()
    extra_fields = extra_fields or []

    for field in model_def.field_names():
        target_norm = _normalize(field)
        if target_norm in normalized_cols:
            mapping[normalized_cols[target_norm]] = field
            continue

        for alias in aliases.get(field, []):
            alias_norm = _normalize(alias)
            if alias_norm in normalized_cols:
                mapping[normalized_cols[alias_norm]] = field
                break

    for field in extra_fields:
        if field in model_def.field_names():
            continue
        target_norm = _normalize(field)
        if target_norm in normalized_cols and normalized_cols[target_norm] not in mapping:
            mapping[normalized_cols[target_norm]] = field

    return mapping


def map_columns(df, mapping):
    return df.rename(columns=mapping)
