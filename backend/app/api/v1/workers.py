import os
import sys
import uuid
import subprocess
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import ResourceNotFoundException
from app.models.worker import Worker
from app.models.enums import WorkerStatus
from app.schemas.worker import WorkerResponse
from app.schemas.common import ApiResponse
from app.services.auth_logic import get_current_user
from app.models.user import User

router = APIRouter(prefix="/workers", tags=["Workers Fleet"])


@router.get("", response_model=ApiResponse[List[WorkerResponse]])
async def list_workers(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await session.execute(select(Worker).order_by(Worker.started_at.desc()))
    workers = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    responses = []
    for w in workers:
        last_hb = w.last_heartbeat_at.replace(tzinfo=timezone.utc) if w.last_heartbeat_at.tzinfo is None else w.last_heartbeat_at
        started = w.started_at.replace(tzinfo=timezone.utc) if w.started_at.tzinfo is None else w.started_at
        
        is_stale = (now - last_hb).total_seconds() > 30
        is_healthy = (w.status in (WorkerStatus.IDLE, WorkerStatus.BUSY)) and not is_stale
        uptime = int((now - started).total_seconds())

        resp = WorkerResponse.model_validate(w)
        resp.is_healthy = is_healthy
        resp.uptime_seconds = uptime
        responses.append(resp)

    return ApiResponse(success=True, data=responses)


@router.get("/{worker_id}", response_model=ApiResponse[WorkerResponse])
async def get_worker(
    worker_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    worker = await session.get(Worker, worker_id)
    if not worker:
        raise ResourceNotFoundException(f"Worker with ID '{worker_id}' not found")

    now = datetime.now(timezone.utc)
    last_hb = worker.last_heartbeat_at.replace(tzinfo=timezone.utc) if worker.last_heartbeat_at.tzinfo is None else worker.last_heartbeat_at
    started = worker.started_at.replace(tzinfo=timezone.utc) if worker.started_at.tzinfo is None else worker.started_at
    
    is_stale = (now - last_hb).total_seconds() > 30
    is_healthy = (worker.status in (WorkerStatus.IDLE, WorkerStatus.BUSY)) and not is_stale
    uptime = int((now - started).total_seconds())

    resp = WorkerResponse.model_validate(worker)
    resp.is_healthy = is_healthy
    resp.uptime_seconds = uptime
    return ApiResponse(success=True, data=resp)


@router.post("/spawn", response_model=ApiResponse[str], status_code=status.HTTP_201_CREATED)
async def spawn_worker(
    current_user: User = Depends(get_current_user)
):
    """
    Dynamically spawns a new worker_cli.py background process.
    """
    worker_id = f"dynamic-node-{uuid.uuid4().hex[:6]}"
    
    # Path to the worker_cli.py script
    # __file__ is backend/app/api/v1/workers.py
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    script_path = os.path.join(backend_dir, "worker_cli.py")

    cmd = [
        sys.executable, 
        script_path, 
        "--worker-id", worker_id, 
        "--concurrency", "5"
    ]
    
    # Run fully detached so it outlives the request
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
    
    subprocess.Popen(
        cmd,
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags
    )
    
    return ApiResponse(success=True, message=f"Spawned new worker node: {worker_id}", data=worker_id)
