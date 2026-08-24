import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ResourceNotFoundException,
    QueuePausedException,
    IdempotencyConflictException,
    IllegalJobStateTransitionException,
)
from app.core.logging import logger
from app.models.job import Job
from app.models.queue import Queue
from app.models.project import Project
from app.models.execution import JobExecution, JobLog
from app.models.enums import JobStatus, QueueStatus, ExecutionStatus
from app.schemas.job import (
    JobCreateRequest,
    BatchJobCreateRequest,
    JobResponse,
    JobDetailResponse,
    JobTimelineItem,
    JobExecutionResponse,
    JobLogResponse,
    BatchJobResponse,
)
from app.schemas.common import PagedResponse
from app.services.status_updater import JobStateMachine


class JobService:

    @staticmethod
    async def submit_job(session: AsyncSession, request: JobCreateRequest) -> JobResponse:
        # 1. Check Idempotency
        if request.idempotency_key:
            existing = await session.scalar(
                select(Job).where(
                    Job.project_id == request.project_id,
                    Job.idempotency_key == request.idempotency_key
                )
            )
            if existing:
                logger.info(f"Idempotent job submission returned existing job {existing.id}")
                return JobResponse.model_validate(existing)

        # 2. Check Queue
        queue = await session.get(Queue, request.queue_id)
        if not queue:
            raise ResourceNotFoundException(f"Queue with ID '{request.queue_id}' not found")
        if queue.status == QueueStatus.PAUSED:
            raise QueuePausedException(f"Queue '{queue.name}' is currently PAUSED")

        # 3. Check Project
        project = await session.get(Project, request.project_id)
        if not project:
            raise ResourceNotFoundException(f"Project with ID '{request.project_id}' not found")

        now = datetime.now(timezone.utc)
        scheduled_at = request.scheduled_at or now

        initial_status = JobStatus.SCHEDULED if (scheduled_at > now or request.cron_expression) else JobStatus.QUEUED

        job = Job(
            queue_id=request.queue_id,
            project_id=request.project_id,
            idempotency_key=request.idempotency_key,
            parent_job_id=request.parent_job_id,
            job_type=request.job_type,
            payload=request.payload,
            priority=request.priority,
            status=initial_status,
            scheduled_at=scheduled_at,
            cron_expression=request.cron_expression,
            attempt_count=0,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        try:
            from app.core.events import event_bus
            event_bus.publish_new_job()
        except ImportError:
            pass

        logger.info(f"Job {job.id} submitted (Type: {job.job_type}, Queue: {queue.name}) with status '{job.status.value}'")
        return JobResponse.model_validate(job)

    @staticmethod
    async def submit_batch(session: AsyncSession, request: BatchJobCreateRequest) -> BatchJobResponse:
        job_ids = []
        now = datetime.now(timezone.utc)

        for item in request.jobs:
            queue = await session.get(Queue, item.queue_id)
            if not queue or queue.status == QueueStatus.PAUSED:
                continue

            scheduled_at = item.scheduled_at or now
            initial_status = JobStatus.SCHEDULED if (scheduled_at > now or item.cron_expression) else JobStatus.QUEUED

            job = Job(
                queue_id=item.queue_id,
                project_id=item.project_id,
                idempotency_key=item.idempotency_key,
                job_type=item.job_type,
                payload=item.payload,
                priority=item.priority,
                status=initial_status,
                scheduled_at=scheduled_at,
                cron_expression=item.cron_expression,
                attempt_count=0,
                max_retries=item.max_retries,
                timeout_seconds=item.timeout_seconds,
            )
            session.add(job)
            await session.flush()
            job_ids.append(job.id)

        await session.commit()
        return BatchJobResponse(
            batch_name=request.batch_name,
            total_jobs=len(request.jobs),
            successful_submissions=len(job_ids),
            job_ids=job_ids
        )

    @staticmethod
    async def get_job(session: AsyncSession, job_id: uuid.UUID) -> JobResponse:
        job = await session.get(Job, job_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")
        return JobResponse.model_validate(job)

    @staticmethod
    async def get_job_detail(session: AsyncSession, job_id: uuid.UUID) -> JobDetailResponse:
        job = await session.get(
            Job,
            job_id,
            options=[
                selectinload(Job.executions).selectinload(JobExecution.logs)
            ]
        )
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        # Build chronological timeline
        timeline: List[JobTimelineItem] = []
        timeline.append(JobTimelineItem(
            timestamp=job.created_at,
            event="JOB_CREATED",
            status="QUEUED" if not job.cron_expression else "SCHEDULED",
            details=f"Job initialized with type {job.job_type} on queue"
        ))

        if job.claimed_at and job.claimed_by_worker_id:
            timeline.append(JobTimelineItem(
                timestamp=job.claimed_at,
                event="JOB_CLAIMED",
                status="CLAIMED",
                worker_id=job.claimed_by_worker_id,
                details=f"Claimed by worker {job.claimed_by_worker_id}"
            ))

        for ex in job.executions:
            timeline.append(JobTimelineItem(
                timestamp=ex.started_at,
                event=f"ATTEMPT_{ex.attempt_number}_STARTED",
                status="RUNNING",
                worker_id=ex.worker_id,
                attempt_number=ex.attempt_number,
                details=f"Execution attempt #{ex.attempt_number} dispatched"
            ))
            if ex.finished_at:
                event_name = f"ATTEMPT_{ex.attempt_number}_{ex.status.value}"
                timeline.append(JobTimelineItem(
                    timestamp=ex.finished_at,
                    event=event_name,
                    status=ex.status.value,
                    worker_id=ex.worker_id,
                    attempt_number=ex.attempt_number,
                    details=ex.error_message or f"Completed in {ex.duration_ms}ms"
                ))

        if job.completed_at:
            timeline.append(JobTimelineItem(
                timestamp=job.completed_at,
                event="JOB_COMPLETED",
                status="COMPLETED",
                details="Job completed successfully"
            ))
        elif job.failed_at and job.status == JobStatus.DEAD_LETTER:
            timeline.append(JobTimelineItem(
                timestamp=job.failed_at,
                event="MOVED_TO_DLQ",
                status="DEAD_LETTER",
                details=f"Retries exhausted. Reason: {job.error_message}"
            ))

        timeline.sort(key=lambda x: x.timestamp)

        # Convert executions to schema
        execution_schemas = []
        for ex in job.executions:
            ex_schema = JobExecutionResponse.model_validate(ex)
            ex_schema.logs = [JobLogResponse.model_validate(l) for l in ex.logs]
            execution_schemas.append(ex_schema)

        detail_dict = JobResponse.model_validate(job).model_dump()
        return JobDetailResponse(
            **detail_dict,
            payload=job.payload,
            executions=execution_schemas,
            timeline=timeline
        )

    @staticmethod
    async def list_jobs(
        session: AsyncSession,
        page: int = 0,
        size: int = 20,
        status: Optional[JobStatus] = None,
        queue_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        worker_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PagedResponse[JobResponse]:
        query = select(Job)
        count_query = select(func.count(Job.id))

        if status:
            query = query.where(Job.status == status)
            count_query = count_query.where(Job.status == status)
        if queue_id:
            query = query.where(Job.queue_id == queue_id)
            count_query = count_query.where(Job.queue_id == queue_id)
        if project_id:
            query = query.where(Job.project_id == project_id)
            count_query = count_query.where(Job.project_id == project_id)
        if worker_id:
            query = query.where(Job.claimed_by_worker_id == worker_id)
            count_query = count_query.where(Job.claimed_by_worker_id == worker_id)
        if search:
            search_filter = or_(
                Job.job_type.ilike(f"%{search}%"),
                Job.idempotency_key.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_elements = (await session.scalar(count_query)) or 0
        total_pages = (total_elements + size - 1) // size if total_elements > 0 else 0

        query = query.order_by(Job.created_at.desc()).offset(page * size).limit(size)
        result = await session.execute(query)
        jobs = result.scalars().all()

        return PagedResponse[JobResponse](
            content=[JobResponse.model_validate(j) for j in jobs],
            page=page,
            size=size,
            totalElements=total_elements,
            totalPages=total_pages,
            last=(page >= total_pages - 1),
            first=(page == 0)
        )

    @staticmethod
    async def cancel_job(session: AsyncSession, job_id: uuid.UUID) -> JobResponse:
        job = await session.get(Job, job_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        JobStateMachine.validate_transition(job.status, JobStatus.CANCELLED)
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(job)
        return JobResponse.model_validate(job)

    @staticmethod
    async def retry_job_manually(session: AsyncSession, job_id: uuid.UUID) -> JobResponse:
        job = await session.get(Job, job_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        JobStateMachine.validate_transition(job.status, JobStatus.QUEUED)
        now = datetime.now(timezone.utc)
        job.status = JobStatus.QUEUED
        job.scheduled_at = now
        job.claimed_by_worker_id = None
        job.claimed_at = None
        job.failed_at = None
        job.error_message = None
        job.updated_at = now

        await session.commit()
        await session.refresh(job)
        return JobResponse.model_validate(job)
