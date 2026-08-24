import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, Integer, BigInteger, DateTime, Enum, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.database import Base
from app.models.base import BaseModel, utc_now
from app.models.enums import ExecutionStatus



if TYPE_CHECKING:
    from app.models.organization import Project
    from app.models.queue import Queue
    from app.models.job import Job
    from app.models.retry_policy import RetryPolicy
    from app.models.dlq import DLQEntry
    from app.models.worker import Worker

class JobExecution(BaseModel):
    __tablename__ = "job_executions"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uk_job_attempt"),
        Index("idx_executions_job_id", "job_id", "attempt_number"),
        Index("idx_executions_worker", "worker_id", "started_at"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="execution_status_enum", native_enum=False),
        default=ExecutionStatus.RUNNING,
        nullable=False,
        index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="executions")
    logs: Mapped[List["JobLog"]] = relationship(
        "JobLog",
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="JobLog.timestamp.asc()"
    )


class JobLog(Base):
    __tablename__ = "job_logs"
    __table_args__ = (
        Index("idx_job_logs_exec", "execution_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("job_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    log_level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )

    execution: Mapped["JobExecution"] = relationship("JobExecution", back_populates="logs")
