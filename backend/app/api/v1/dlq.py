import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import DLQResolutionStatus
from app.schemas.dlq import DLQResponse, DLQResolutionRequest
from app.schemas.common import ApiResponse, PagedResponse
from app.services.failed_jobs_logic import DLQService
from app.services.auth_logic import get_current_user
from app.models.user import User

router = APIRouter(prefix="/dlq", tags=["Dead Letter Queue"])


@router.get("", response_model=ApiResponse[PagedResponse[DLQResponse]])
async def list_dlq(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    queue_id: Optional[uuid.UUID] = None,
    resolution_status: Optional[DLQResolutionStatus] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paged = await DLQService.list_dlq_entries(
        session=session,
        page=page,
        size=size,
        queue_id=queue_id,
        resolution_status=resolution_status
    )
    return ApiResponse(success=True, data=paged)


@router.post("/{dlq_id}/replay", response_model=ApiResponse[DLQResponse])
async def replay_dlq_entry(
    dlq_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    replayed = await DLQService.replay_dlq_job(session, dlq_id)
    return ApiResponse(success=True, message="Job replayed from DLQ to active queue", data=replayed)


@router.post("/{dlq_id}/archive", response_model=ApiResponse[DLQResponse])
async def archive_dlq_entry(
    dlq_id: uuid.UUID,
    request: DLQResolutionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    archived = await DLQService.archive_dlq_job(session, dlq_id, request)
    return ApiResponse(success=True, message="DLQ entry archived", data=archived)
