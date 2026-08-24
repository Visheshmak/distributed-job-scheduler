from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import WorkerStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Worker(Base):
    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    shard_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status_enum", native_enum=False),
        default=WorkerStatus.STARTING,
        nullable=False,
        index=True
    )
    concurrency: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    current_running_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
