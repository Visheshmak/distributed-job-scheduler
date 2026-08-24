import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException
from app.models.queue import Queue
from app.models.project import Project
from app.models.retry_policy import RetryPolicy
from app.models.job import Job
from app.models.enums import QueueStatus, JobStatus
from app.schemas.queue import (
    QueueCreateRequest,
    QueueUpdateRequest,
    QueueResponse,
    RetryPolicyCreateRequest,
    RetryPolicyResponse,
)


class QueueService:

    @staticmethod
    async def create_retry_policy(session: AsyncSession, request: RetryPolicyCreateRequest) -> RetryPolicyResponse:
        existing = await session.scalar(select(RetryPolicy).where(RetryPolicy.name == request.name))
        if existing:
            raise DuplicateResourceException(f"Retry policy with name '{request.name}' already exists")

        policy = RetryPolicy(
            name=request.name,
            strategy=request.strategy,
            max_attempts=request.max_attempts,
            base_delay_ms=request.base_delay_ms,
            max_delay_ms=request.max_delay_ms,
            jitter_factor=request.jitter_factor,
        )
        session.add(policy)
        await session.commit()
        await session.refresh(policy)
        return RetryPolicyResponse.model_validate(policy)

    @staticmethod
    async def list_retry_policies(session: AsyncSession) -> List[RetryPolicyResponse]:
        result = await session.execute(select(RetryPolicy).order_by(RetryPolicy.name.asc()))
        policies = result.scalars().all()
        return [RetryPolicyResponse.model_validate(p) for p in policies]

    @staticmethod
    async def create_queue(session: AsyncSession, request: QueueCreateRequest) -> QueueResponse:
        project = await session.get(Project, request.project_id)
        if not project:
            raise ResourceNotFoundException(f"Project with ID '{request.project_id}' not found")

        if request.retry_policy_id:
            policy = await session.get(RetryPolicy, request.retry_policy_id)
            if not policy:
                raise ResourceNotFoundException(f"Retry policy with ID '{request.retry_policy_id}' not found")

        existing = await session.scalar(
            select(Queue).where(Queue.project_id == request.project_id, Queue.name == request.name)
        )
        if existing:
            raise DuplicateResourceException(f"Queue with name '{request.name}' already exists in this project")

        queue = Queue(
            project_id=request.project_id,
            retry_policy_id=request.retry_policy_id,
            name=request.name,
            priority=request.priority,
            max_concurrency=request.max_concurrency,
            status=request.status,
        )
        session.add(queue)
        await session.commit()
        await session.refresh(queue, ["retry_policy"])
        return QueueResponse.model_validate(queue)

    @staticmethod
    async def update_queue(session: AsyncSession, queue_id: uuid.UUID, request: QueueUpdateRequest) -> QueueResponse:
        queue = await session.get(Queue, queue_id, options=[selectinload(Queue.retry_policy)])
        if not queue:
            raise ResourceNotFoundException(f"Queue with ID '{queue_id}' not found")

        if request.priority is not None:
            queue.priority = request.priority
        if request.max_concurrency is not None:
            queue.max_concurrency = request.max_concurrency
        if request.retry_policy_id is not None:
            policy = await session.get(RetryPolicy, request.retry_policy_id)
            if not policy:
                raise ResourceNotFoundException(f"Retry policy with ID '{request.retry_policy_id}' not found")
            queue.retry_policy_id = request.retry_policy_id

        await session.commit()
        await session.refresh(queue, ["retry_policy"])
        return QueueResponse.model_validate(queue)

    @staticmethod
    async def set_queue_status(session: AsyncSession, queue_id: uuid.UUID, status: QueueStatus) -> QueueResponse:
        queue = await session.get(Queue, queue_id, options=[selectinload(Queue.retry_policy)])
        if not queue:
            raise ResourceNotFoundException(f"Queue with ID '{queue_id}' not found")

        queue.status = status
        await session.commit()
        await session.refresh(queue, ["retry_policy"])
        return QueueResponse.model_validate(queue)

    @staticmethod
    async def get_queue(session: AsyncSession, queue_id: uuid.UUID) -> QueueResponse:
        queue = await session.get(Queue, queue_id, options=[selectinload(Queue.retry_policy)])
        if not queue:
            raise ResourceNotFoundException(f"Queue with ID '{queue_id}' not found")

        resp = QueueResponse.model_validate(queue)
        
        # Populate counts
        counts = await session.execute(
            select(Job.status, func.count(Job.id))
            .where(Job.queue_id == queue_id)
            .group_by(Job.status)
        )
        for st, cnt in counts.all():
            if st == JobStatus.QUEUED:
                resp.queued_count = cnt
            elif st == JobStatus.RUNNING:
                resp.running_count = cnt
            elif st == JobStatus.COMPLETED:
                resp.completed_count = cnt
            elif st in (JobStatus.FAILED, JobStatus.DEAD_LETTER):
                resp.failed_count += cnt
                
        return resp

    @staticmethod
    async def list_queues(session: AsyncSession, project_id: Optional[uuid.UUID] = None) -> List[QueueResponse]:
        query = select(Queue).options(selectinload(Queue.retry_policy))
        if project_id:
            query = query.where(Queue.project_id == project_id)
        query = query.order_by(Queue.priority.desc(), Queue.name.asc())

        result = await session.execute(query)
        queues = result.scalars().all()

        responses = []
        for q in queues:
            resp = QueueResponse.model_validate(q)
            # Job counts per queue
            counts = await session.execute(
                select(Job.status, func.count(Job.id))
                .where(Job.queue_id == q.id)
                .group_by(Job.status)
            )
            for st, cnt in counts.all():
                if st == JobStatus.QUEUED:
                    resp.queued_count = cnt
                elif st == JobStatus.RUNNING:
                    resp.running_count = cnt
                elif st == JobStatus.COMPLETED:
                    resp.completed_count = cnt
                elif st in (JobStatus.FAILED, JobStatus.DEAD_LETTER):
                    resp.failed_count = (resp.failed_count or 0) + cnt
            responses.append(resp)

        return responses
