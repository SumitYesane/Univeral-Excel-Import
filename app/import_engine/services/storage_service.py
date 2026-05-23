import os
import shutil
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.utils.exceptions import StorageException


def _safe_filename(name: str) -> str:
    filename = Path(name).name.strip().replace(" ", "_")
    return "".join(ch for ch in filename if ch.isalnum() or ch in {"-", "_", "."}) or "upload.bin"


class StorageService:
    async def save_upload(self, file: UploadFile, tenant_id: str) -> str:
        extension = Path(file.filename or "").suffix.lower()
        if extension not in settings.ALLOWED_FILE_EXTENSIONS:
            raise StorageException(f"Unsupported file extension '{extension}'")

        settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        tenant_dir = (settings.STORAGE_ROOT / tenant_id).resolve()
        tenant_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _safe_filename(file.filename or "upload.bin")
        path = (tenant_dir / safe_name).resolve()
        if tenant_dir not in path.parents and path != tenant_dir:
            raise StorageException("Invalid upload path")

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        bytes_written = 0
        with path.open("wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    path.unlink(missing_ok=True)
                    raise StorageException("Uploaded file exceeds configured size limit")
                handle.write(chunk)
        await file.close()
        return str(path)

    def download_to_local(self, file_url: str, tenant_id: str) -> str:
        path = Path(file_url).resolve()
        if not path.exists():
            raise StorageException(f"File does not exist: {file_url}")
        return str(path)

    def upload_error_file(self, local_path: str, tenant_id: str) -> str:
        settings.ERROR_ROOT.mkdir(parents=True, exist_ok=True)
        target_dir = (settings.ERROR_ROOT / tenant_id).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        source = Path(local_path).resolve()
        target = (target_dir / source.name).resolve()
        shutil.copy2(source, target)
        return str(target)
