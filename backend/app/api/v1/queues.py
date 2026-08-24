import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import QueueStatus
from app.schemas.queue import (
    QueueCreateRequest,
    QueueUpdateRequest,
    QueueResponse,
    RetryPolicyCreateRequest,
    RetryPolicyResponse,
)
from app.schemas.common import ApiResponse
from app.services.queues_logic import QueueService
from app.services.auth_logic import get_current_user
from app.models.user import User

router = APIRouter(prefix="/queues", tags=["Queues & Policies"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/retry-policies", response_model=ApiResponse[RetryPolicyResponse], status_code=status.HTTP_201_CREATED)
async def create_retry_policy(
    request: RetryPolicyCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    policy = await QueueService.create_retry_policy(session, request)
    return ApiResponse(success=True, data=policy)


@router.get("/retry-policies", response_model=ApiResponse[List[RetryPolicyResponse]])
async def list_retry_policies(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    policies = await QueueService.list_retry_policies(session)
    return ApiResponse(success=True, data=policies)


@router.post("", response_model=ApiResponse[QueueResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_queue(
    payload: QueueCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    queue = await QueueService.create_queue(session, payload)
    return ApiResponse(success=True, data=queue)


@router.get("", response_model=ApiResponse[List[QueueResponse]])
async def list_queues(
    project_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    queues = await QueueService.list_queues(session, project_id=project_id)
    return ApiResponse(success=True, data=queues)


@router.get("/{queue_id}", response_model=ApiResponse[QueueResponse])
async def get_queue(
    queue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    queue = await QueueService.get_queue(session, queue_id)
    return ApiResponse(success=True, data=queue)


@router.patch("/{queue_id}", response_model=ApiResponse[QueueResponse])
async def update_queue(
    queue_id: uuid.UUID,
    request: QueueUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    queue = await QueueService.update_queue(session, queue_id, request)
    return ApiResponse(success=True, data=queue)


@router.post("/{queue_id}/pause", response_model=ApiResponse[QueueResponse])
async def pause_queue(
    queue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    queue = await QueueService.set_queue_status(session, queue_id, QueueStatus.PAUSED)
    return ApiResponse(success=True, message=f"Queue '{queue.name}' PAUSED", data=queue)


@router.post("/{queue_id}/resume", response_model=ApiResponse[QueueResponse])
async def resume_queue(
    queue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    queue = await QueueService.set_queue_status(session, queue_id, QueueStatus.ACTIVE)
    return ApiResponse(success=True, message=f"Queue '{queue.name}' RESUMED (ACTIVE)", data=queue)
