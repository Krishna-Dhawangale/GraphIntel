import io
from typing import BinaryIO, Union

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging import logger
from app.providers.storage.base import StorageProvider


class MinIOStorage(StorageProvider):
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.secure = settings.MINIO_USE_SSL
        self.bucket = settings.MINIO_BUCKET_NAME

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
        except Exception as e:
            logger.warning(f"Could not connect or ensure MinIO bucket '{self.bucket}': {e}")

    async def upload(
        self,
        file_data: Union[bytes, BinaryIO],
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        if isinstance(file_data, bytes):
            data_stream = io.BytesIO(file_data)
            length = len(file_data)
        else:
            file_data.seek(0, io.SEEK_END)
            length = file_data.tell()
            file_data.seek(0)
            data_stream = file_data

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=destination_path,
            data=data_stream,
            length=length,
            content_type=content_type,
        )
        return destination_path

    async def download(self, source_path: str) -> bytes:
        response = None
        try:
            response = self.client.get_object(self.bucket, source_path)
            return response.read()
        except S3Error as e:
            logger.error(f"MinIO download failed for {source_path}: {e}")
            raise FileNotFoundError(f"File not found in storage: {source_path}")
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    async def delete(self, source_path: str) -> bool:
        try:
            self.client.remove_object(self.bucket, source_path)
            return True
        except Exception as e:
            logger.error(f"MinIO delete error for {source_path}: {e}")
            return False

    async def exists(self, source_path: str) -> bool:
        try:
            self.client.stat_object(self.bucket, source_path)
            return True
        except Exception:
            return False
