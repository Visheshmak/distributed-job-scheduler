import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, DateTime, Enum, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import BaseModel, utc_now
from app.models.enums import DLQResolutionStatus



if TYPE_CHECKING:
    from app.models.organization import Project
    from app.models.queue import Queue
    from app.models.job import Job
    from app.models.retry_policy import RetryPolicy
    from app.models.execution import JobExecution
    from app.models.worker import Worker

class DLQEntry(BaseModel):
    __tablename__ = "dlq_entries"
    __table_args__ = (
        Index("idx_dlq_queue_failed", "queue_id", "failed_at"),
        Index("idx_dlq_status", "resolution_status", "failed_at"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    final_exception: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_status: Mapped[DLQResolutionStatus] = mapped_column(
        Enum(DLQResolutionStatus, name="dlq_resolution_status_enum", native_enum=False),
        default=DLQResolutionStatus.UNRESOLVED,
        nullable=False,
        index=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_root_cause_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="dlq_entry")
    queue: Mapped["Queue"] = relationship("Queue")
