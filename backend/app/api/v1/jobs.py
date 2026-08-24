import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import JobStatus
from app.schemas.job import (
    JobCreateRequest,
    BatchJobCreateRequest,
    JobResponse,
    JobDetailResponse,
    BatchJobResponse,
)
from app.schemas.common import ApiResponse, PagedResponse
from app.services.jobs_logic import JobService
from app.services.auth_logic import get_current_user
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["Jobs Management"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=ApiResponse[JobResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("5/second")
async def submit_job(
    payload: JobCreateRequest,
    request: Request,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if idempotency_key_header and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key_header

    job = await JobService.submit_job(session, payload)
    return ApiResponse(success=True, message="Job submitted successfully", data=job)


@router.post("/batch", response_model=ApiResponse[BatchJobResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("2/second")
async def submit_batch_jobs(
    payload: BatchJobCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    batch_resp = await JobService.submit_batch(session, payload)
    return ApiResponse(success=True, message=f"Batch '{payload.batch_name}' submitted", data=batch_resp)


@router.get("", response_model=ApiResponse[PagedResponse[JobResponse]])
async def list_jobs(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = None,
    queue_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    worker_id: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paged = await JobService.list_jobs(
        session=session,
        page=page,
        size=size,
        status=status,
        queue_id=queue_id,
        project_id=project_id,
        worker_id=worker_id,
        search=search
    )
    return ApiResponse(success=True, data=paged)


@router.get("/{job_id}", response_model=ApiResponse[JobResponse])
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = await JobService.get_job(session, job_id)
    return ApiResponse(success=True, data=job)


@router.get("/{job_id}/detail", response_model=ApiResponse[JobDetailResponse])
async def get_job_detail(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    detail = await JobService.get_job_detail(session, job_id)
    return ApiResponse(success=True, data=detail)


@router.post("/{job_id}/retry", response_model=ApiResponse[JobResponse])
async def retry_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    retried = await JobService.retry_job_manually(session, job_id)
    return ApiResponse(success=True, message="Job reset to QUEUED for retry", data=retried)


@router.post("/{job_id}/cancel", response_model=ApiResponse[JobResponse])
async def cancel_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cancelled = await JobService.cancel_job(session, job_id)
    return ApiResponse(success=True, message="Job CANCELLED", data=cancelled)
