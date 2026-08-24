import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from sqlalchemy import String, Integer, DateTime, Enum, JSON, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import BaseModel, utc_now
from app.models.enums import JobStatus



if TYPE_CHECKING:
    from app.models.organization import Project
    from app.models.queue import Queue
    from app.models.retry_policy import RetryPolicy
    from app.models.execution import JobExecution
    from app.models.dlq import DLQEntry
    from app.models.worker import Worker

class Job(BaseModel):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="uk_job_project_idempotency"),
        Index("idx_jobs_claim", "queue_id", "status", "scheduled_at", "priority", "created_at"),
        Index("idx_jobs_status_scheduled", "status", "scheduled_at"),
        Index("idx_jobs_worker_status", "claimed_by_worker_id", "status"),
        Index("idx_jobs_project_created", "project_id", "created_at"),
    )

    queue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    parent_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", native_enum=False),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    
    claimed_by_worker_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("workers.worker_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    queue: Mapped["Queue"] = relationship("Queue", back_populates="jobs")
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")
    worker: Mapped[Optional["Worker"]] = relationship("Worker")
    executions: Mapped[List["JobExecution"]] = relationship(
        "JobExecution",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobExecution.attempt_number.asc()"
    )
    dlq_entry: Mapped[Optional["DLQEntry"]] = relationship(
        "DLQEntry",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan"
    )
