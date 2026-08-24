from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import WorkerStatus


class WorkerResponse(BaseModel):
    worker_id: str
    shard_id: int = 0
    hostname: str
    status: WorkerStatus
    concurrency: int
    current_running_jobs: int
    last_heartbeat_at: datetime
    started_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None
    is_healthy: bool = True
    uptime_seconds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class WorkerHeartbeatRequest(BaseModel):
    status: Optional[WorkerStatus] = None
    current_running_jobs: Optional[int] = Field(default=None, ge=0)
    metadata_json: Optional[Dict[str, Any]] = None
