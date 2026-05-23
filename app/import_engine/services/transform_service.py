import pandas as pd


def _string_series(df, column_name: str) -> pd.Series:
    return df[column_name].fillna("").astype(str)


def apply_transforms(df, rules):
    transformed = df.copy()
    for rule in rules:
        if rule.source and rule.source not in transformed.columns:
            continue
        if rule.type == "uppercase":
            target = rule.target or rule.source
            transformed[target] = _string_series(transformed, rule.source).str.upper()
        elif rule.type == "lowercase":
            target = rule.target or rule.source
            transformed[target] = _string_series(transformed, rule.source).str.lower()
        elif rule.type == "split" and rule.targets:
            parts = _string_series(transformed, rule.source).str.split(rule.delimiter, expand=True)
            for i, target in enumerate(rule.targets):
                transformed[target] = parts[i] if i in parts.columns else None
    return transformed
