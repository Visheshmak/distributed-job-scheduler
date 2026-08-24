from typing import List, Dict, Any
from pydantic import BaseModel


class SystemThroughputMetric(BaseModel):
    timestamp: str
    completed_count: int
    failed_count: int


class QueueDepthMetric(BaseModel):
    queue_id: str
    queue_name: str
    queued_count: int
    running_count: int


class OverviewMetricsResponse(BaseModel):
    total_jobs: int
    queued_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    dlq_jobs: int
    active_workers: int
    total_workers: int
    system_load_pct: float
    queues: List[QueueDepthMetric] = []
    throughput_history: List[SystemThroughputMetric] = []
