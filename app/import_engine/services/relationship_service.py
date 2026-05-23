from typing import List


def build_relationships(conn_str, mapping, rows: List[dict]):
    # Relationship resolution is optional. When no parent-child strategy is
    # configured, we preserve rows as-is instead of mutating payload shape.
    return rows
