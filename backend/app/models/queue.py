import uuid
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, Integer, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import BaseModel
from app.models.enums import QueueStatus



if TYPE_CHECKING:
    from app.models.organization import Project
    from app.models.job import Job
    from app.models.retry_policy import RetryPolicy
    from app.models.execution import JobExecution
    from app.models.dlq import DLQEntry
    from app.models.worker import Worker

class Queue(BaseModel):
    __tablename__ = "queues"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uk_queue_project_name"),
    )

    shard_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    retry_policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("retry_policies.id", ondelete="SET NULL"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus, name="queue_status_enum", native_enum=False),
        default=QueueStatus.ACTIVE,
        nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="queues")
    retry_policy: Mapped[Optional["RetryPolicy"]] = relationship("RetryPolicy")
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="queue")
