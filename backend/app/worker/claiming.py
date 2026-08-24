from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.job import Job
from app.models.queue import Queue
from app.models.enums import JobStatus, QueueStatus


async def claim_available_jobs(
    session: AsyncSession,
    worker_id: str,
    shard_id: int = 0,
    limit: int = 5
) -> List[Job]:
    """
    Atomically claims available QUEUED jobs using PostgreSQL's FOR UPDATE SKIP LOCKED.
    
    Guarantees:
    - Zero duplicate claims among concurrent worker nodes.
    - Zero lock contention / blocking since locked rows are skipped immediately.
    - Strict prioritization: Queue Priority DESC -> Job Priority DESC -> Created At ASC.
    """
    if limit <= 0:
        return []

    now = datetime.now(timezone.utc)

    ParentJob = aliased(Job)
    
    # Subquery / Statement selecting claimable jobs with row-level locks
    claim_query = (
        select(Job)
        .join(Queue, Job.queue_id == Queue.id)
        .outerjoin(ParentJob, Job.parent_job_id == ParentJob.id)
        .where(
            and_(
                Queue.status == QueueStatus.ACTIVE,
                Queue.shard_id == shard_id,
                Job.status == JobStatus.QUEUED,
                Job.scheduled_at <= now,
                or_(Job.parent_job_id.is_(None), ParentJob.status == JobStatus.COMPLETED)
            )
        )
        .order_by(
            Queue.priority.desc(),
            Job.priority.desc(),
            Job.created_at.asc()
        )
    )

    # In PostgreSQL production environment, acquire row locks skipping already locked rows
    bind = session.bind or session.get_bind()
    if bind and "postgresql" in bind.dialect.name:
        claim_query = claim_query.with_for_update(skip_locked=True)

    claim_query = claim_query.limit(limit)

    result = await session.execute(claim_query)
    jobs = result.scalars().all()

    if not jobs:
        return []

    for job in jobs:
        job.status = JobStatus.CLAIMED
        job.claimed_by_worker_id = worker_id
        job.claimed_at = now
        job.attempt_count += 1
        job.updated_at = now

    await session.commit()
    logger.info(f"Worker '{worker_id}' atomically claimed {len(jobs)} jobs: {[str(j.id) for j in jobs]}")
    return list(jobs)
