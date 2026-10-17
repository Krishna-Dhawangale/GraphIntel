from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.query import GraphPathInfo, QueryMetadata, SourceCitation


class ResearchHistoryItem(BaseModel):
    id: str
    question: str
    answer: str
    answer_preview: str
    retrieval_mode: str
    citations_count: int = 0
    graph_paths_count: int = 0
    status: str = "SUCCESS"
    created_at: datetime


class ResearchHistoryDetail(BaseModel):
    id: str
    user_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    question: str
    answer: str
    retrieval_mode: str
    citations: List[SourceCitation] = Field(default_factory=list)
    graph_paths: List[GraphPathInfo] = Field(default_factory=list)
    metadata: Optional[QueryMetadata] = None
    status: str = "SUCCESS"
    created_at: datetime
    updated_at: datetime


class ResearchHistoryListResponse(BaseModel):
    items: List[ResearchHistoryItem]
    total: int
    skip: int
    limit: int


class MigrateGuestHistoryRequest(BaseModel):
    guest_session_id: Optional[str] = None


class MigrateGuestHistoryResponse(BaseModel):
    migrated_count: int
    message: str
