from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus
from app.schemas.chunk import DocumentChunkResponse


class DocumentBase(BaseModel):
    title: str
    filename: str
    file_size: int
    content_type: str
    status: DocumentStatus
    error_message: Optional[str] = None
    doc_metadata: Dict[str, Any] = {}


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    storage_path: str
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    chunks_count: int = 0
    chunks: Optional[List[DocumentChunkResponse]] = None


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: DocumentStatus
    error_message: Optional[str] = None
    total_chunks: int = 0
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
