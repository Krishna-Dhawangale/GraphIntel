from abc import ABC, abstractmethod
from typing import BinaryIO, Union


class StorageProvider(ABC):
    """Abstract interface for object/file storage providers."""

    @abstractmethod
    async def upload(
        self,
        file_data: Union[bytes, BinaryIO],
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file data to storage and return its path/key."""
        pass

    @abstractmethod
    async def download(self, source_path: str) -> bytes:
        """Download binary file data from storage."""
        pass

    @abstractmethod
    async def delete(self, source_path: str) -> bool:
        """Delete file from storage."""
        pass

    @abstractmethod
    async def exists(self, source_path: str) -> bool:
        """Check if file exists in storage."""
        pass
