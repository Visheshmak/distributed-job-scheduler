from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.queues import router as queues_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.workers import router as workers_router
from app.api.v1.dlq import router as dlq_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.websockets import router as websockets_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(queues_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(workers_router)
api_v1_router.include_router(dlq_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(websockets_router)
