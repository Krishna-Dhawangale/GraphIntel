import shutil
from pathlib import Path
from typing import BinaryIO, Union

from app.core.config import settings
from app.providers.storage.base import StorageProvider


class LocalStorage(StorageProvider):
    """Local disk storage provider for development and testing environments."""

    def __init__(self, base_dir: str = settings.STORAGE_LOCAL_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        # Prevent directory traversal attacks
        clean_path = path.lstrip("/\\")
        return (self.base_dir / clean_path).resolve()

    async def upload(
        self,
        file_data: Union[bytes, BinaryIO],
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        target = self._get_full_path(destination_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file_data, bytes):
            target.write_bytes(file_data)
        else:
            file_data.seek(0)
            with open(target, "wb") as f:
                shutil.copyfileobj(file_data, f)

        return destination_path

    async def download(self, source_path: str) -> bytes:
        target = self._get_full_path(source_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {source_path}")
        return target.read_bytes()

    async def delete(self, source_path: str) -> bool:
        target = self._get_full_path(source_path)
        if target.exists():
            target.unlink()
            return True
        return False

    async def exists(self, source_path: str) -> bool:
        target = self._get_full_path(source_path)
        return target.exists()
