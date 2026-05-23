import hashlib
import json


def compute_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_models(models: list) -> str:
    payload = json.dumps(models, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
