import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import JobStatus, ExecutionStatus


class JobCreateRequest(BaseModel):
    queue_id: uuid.UUID
    project_id: uuid.UUID
    job_type: str = Field(min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=-100, le=100)
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    max_retries: int = Field(default=3, ge=0, le=20)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    idempotency_key: Optional[str] = Field(default=None, max_length=255)
    parent_job_id: Optional[uuid.UUID] = None


class BatchJobCreateRequest(BaseModel):
    batch_name: str = Field(min_length=1, max_length=255)
    jobs: List[JobCreateRequest] = Field(min_length=1, max_length=500)


class JobLogResponse(BaseModel):
    id: int
    execution_id: uuid.UUID
    log_level: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class JobExecutionResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    attempt_number: int
    worker_id: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    logs: Optional[List[JobLogResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class JobTimelineItem(BaseModel):
    timestamp: datetime
    event: str
    status: str
    worker_id: Optional[str] = None
    attempt_number: Optional[int] = None
    details: Optional[str] = None


class JobResponse(BaseModel):
    id: uuid.UUID
    queue_id: uuid.UUID
    project_id: uuid.UUID
    idempotency_key: Optional[str] = None
    job_type: str
    priority: int
    status: JobStatus
    scheduled_at: datetime
    cron_expression: Optional[str] = None
    attempt_count: int
    max_retries: int
    timeout_seconds: int
    claimed_by_worker_id: Optional[str] = None
    claimed_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobDetailResponse(JobResponse):
    payload: Dict[str, Any]
    executions: List[JobExecutionResponse] = []
    timeline: List[JobTimelineItem] = []


class BatchJobResponse(BaseModel):
    batch_name: str
    total_jobs: int
    successful_submissions: int
    job_ids: List[uuid.UUID]
