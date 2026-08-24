import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger
from app.models.dlq import DLQEntry
from app.models.job import Job
from app.models.enums import DLQResolutionStatus, JobStatus
from app.schemas.dlq import DLQResponse, DLQResolutionRequest
from app.schemas.common import PagedResponse


class DLQService:

    @staticmethod
    async def move_to_dlq(
        session: AsyncSession,
        job_id: uuid.UUID,
        failure_reason: str,
        final_exception: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> DLQEntry:
        job = await session.get(Job, job_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        job.status = JobStatus.DEAD_LETTER
        job.failed_at = datetime.now(timezone.utc)
        job.error_message = failure_reason

        dlq_entry = await session.scalar(select(DLQEntry).where(DLQEntry.job_id == job_id))
        if not dlq_entry:
            dlq_entry = DLQEntry(
                job_id=job.id,
                queue_id=job.queue_id,
                failed_at=datetime.now(timezone.utc),
                failure_reason=failure_reason,
                final_exception=final_exception,
                total_attempts=job.attempt_count,
                worker_id=worker_id,
                resolution_status=DLQResolutionStatus.UNRESOLVED,
                ai_root_cause_summary=f"AI Analysis: Job {job.id} failed due to: {failure_reason}. Check dependent services or payload schema.",
            )
            session.add(dlq_entry)
        else:
            dlq_entry.failed_at = datetime.now(timezone.utc)
            dlq_entry.failure_reason = failure_reason
            dlq_entry.final_exception = final_exception
            dlq_entry.total_attempts = job.attempt_count
            dlq_entry.worker_id = worker_id
            dlq_entry.resolution_status = DLQResolutionStatus.UNRESOLVED
            dlq_entry.ai_root_cause_summary = f"AI Analysis: Job {job.id} failed due to: {failure_reason}. Check dependent services or payload schema."

        await session.flush()
        logger.warning(f"Job {job_id} moved to DLQ: {failure_reason}")
        return dlq_entry

    @staticmethod
    async def list_dlq_entries(
        session: AsyncSession,
        page: int = 0,
        size: int = 20,
        queue_id: Optional[uuid.UUID] = None,
        resolution_status: Optional[DLQResolutionStatus] = None
    ) -> PagedResponse[DLQResponse]:
        query = select(DLQEntry)
        count_query = select(func.count(DLQEntry.id))

        if queue_id:
            query = query.where(DLQEntry.queue_id == queue_id)
            count_query = count_query.where(DLQEntry.queue_id == queue_id)
        if resolution_status:
            query = query.where(DLQEntry.resolution_status == resolution_status)
            count_query = count_query.where(DLQEntry.resolution_status == resolution_status)

        total_elements = (await session.scalar(count_query)) or 0
        total_pages = (total_elements + size - 1) // size if total_elements > 0 else 0

        query = query.order_by(DLQEntry.failed_at.desc()).offset(page * size).limit(size)
        result = await session.execute(query)
        entries = result.scalars().all()

        return PagedResponse[DLQResponse](
            content=[DLQResponse.model_validate(e) for e in entries],
            page=page,
            size=size,
            totalElements=total_elements,
            totalPages=total_pages,
            last=(page >= total_pages - 1),
            first=(page == 0)
        )

    @staticmethod
    async def replay_dlq_job(session: AsyncSession, dlq_id: uuid.UUID) -> DLQResponse:
        dlq_entry = await session.get(DLQEntry, dlq_id, options=[selectinload(DLQEntry.job)])
        if not dlq_entry:
            raise ResourceNotFoundException(f"DLQ entry with ID '{dlq_id}' not found")

        job = dlq_entry.job
        now = datetime.now(timezone.utc)
        
        # Reset job for execution
        job.status = JobStatus.QUEUED
        job.scheduled_at = now
        job.claimed_by_worker_id = None
        job.claimed_at = None
        job.failed_at = None
        job.error_message = None
        job.updated_at = now

        dlq_entry.resolution_status = DLQResolutionStatus.REPLAYED
        dlq_entry.resolved_at = now
        dlq_entry.resolution_notes = f"Manually replayed at {now.isoformat()}"

        await session.commit()
        await session.refresh(dlq_entry)
        logger.info(f"Replayed DLQ entry {dlq_id} (Job {job.id}) back to QUEUED status")
        return DLQResponse.model_validate(dlq_entry)

    @staticmethod
    async def archive_dlq_job(session: AsyncSession, dlq_id: uuid.UUID, request: DLQResolutionRequest) -> DLQResponse:
        dlq_entry = await session.get(DLQEntry, dlq_id)
        if not dlq_entry:
            raise ResourceNotFoundException(f"DLQ entry with ID '{dlq_id}' not found")

        now = datetime.now(timezone.utc)
        dlq_entry.resolution_status = DLQResolutionStatus.ARCHIVED
        dlq_entry.resolved_at = now
        dlq_entry.resolution_notes = request.resolution_notes or "Archived by operator"

        await session.commit()
        await session.refresh(dlq_entry)
        return DLQResponse.model_validate(dlq_entry)
