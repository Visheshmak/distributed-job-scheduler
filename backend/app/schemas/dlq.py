import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import DLQResolutionStatus


class DLQResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    queue_id: uuid.UUID
    failed_at: datetime
    failure_reason: str
    final_exception: Optional[str] = None
    total_attempts: int
    worker_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_status: DLQResolutionStatus
    resolution_notes: Optional[str] = None
    ai_root_cause_summary: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DLQResolutionRequest(BaseModel):
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)
