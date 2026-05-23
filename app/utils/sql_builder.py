import re


SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_safe_identifier(value: str) -> bool:
    return bool(SAFE_IDENTIFIER.match(value))
