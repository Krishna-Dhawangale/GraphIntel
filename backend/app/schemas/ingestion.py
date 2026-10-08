from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.ingestion import JobStatus


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    status: JobStatus
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
