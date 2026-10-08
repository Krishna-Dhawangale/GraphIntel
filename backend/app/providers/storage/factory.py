from app.core.config import settings
from app.providers.storage.base import StorageProvider
from app.providers.storage.local_storage import LocalStorage
from app.providers.storage.minio_storage import MinIOStorage


def get_storage_provider() -> StorageProvider:
    """Factory to get configured storage provider (MinIO or Local)."""
    if settings.STORAGE_PROVIDER == "minio":
        try:
            return MinIOStorage()
        except Exception:
            return LocalStorage()
    return LocalStorage()
