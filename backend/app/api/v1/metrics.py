from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.database import get_db
from app.schemas.metrics import OverviewMetricsResponse
from app.schemas.common import ApiResponse
from app.services.stats_logic import MetricsService
from app.services.auth_logic import get_current_user
from app.models.user import User

router = APIRouter(prefix="/metrics", tags=["Observability & Metrics"])


@router.get("/overview", response_model=ApiResponse[OverviewMetricsResponse])
async def get_overview_metrics(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    metrics = await MetricsService.get_overview_metrics(session)
    return ApiResponse(success=True, data=metrics)


@router.get("/prometheus")
def get_prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
