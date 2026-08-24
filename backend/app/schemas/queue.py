import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import QueueStatus, RetryStrategy


class RetryPolicyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    strategy: RetryStrategy = Field(default=RetryStrategy.EXPONENTIAL)
    max_attempts: int = Field(default=3, ge=1, le=20)
    base_delay_ms: int = Field(default=1000, ge=100, le=3600000)
    max_delay_ms: int = Field(default=60000, ge=1000, le=86400000)
    jitter_factor: float = Field(default=0.2, ge=0.0, le=1.0)


class RetryPolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    strategy: RetryStrategy
    max_attempts: int
    base_delay_ms: int
    max_delay_ms: int
    jitter_factor: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueueCreateRequest(BaseModel):
    project_id: uuid.UUID
    shard_id: int = Field(default=0)
    shard_id: int
    shard_id: int = Field(default=0)
    retry_policy_id: Optional[uuid.UUID] = None
    name: str = Field(min_length=2, max_length=255)
    priority: int = Field(default=0, ge=-100, le=100)
    max_concurrency: int = Field(default=10, ge=1, le=1000)
    status: QueueStatus = Field(default=QueueStatus.ACTIVE)


class QueueUpdateRequest(BaseModel):
    priority: Optional[int] = Field(default=None, ge=-100, le=100)
    max_concurrency: Optional[int] = Field(default=None, ge=1, le=1000)
    retry_policy_id: Optional[uuid.UUID] = None


class QueueResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    shard_id: int = Field(default=0)
    shard_id: int
    shard_id: int = Field(default=0)
    retry_policy_id: Optional[uuid.UUID] = None
    name: str
    priority: int
    max_concurrency: int
    status: QueueStatus
    created_at: datetime
    updated_at: datetime
    retry_policy: Optional[RetryPolicyResponse] = None
    
    queued_count: Optional[int] = 0
    running_count: Optional[int] = 0
    completed_count: Optional[int] = 0
    failed_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
