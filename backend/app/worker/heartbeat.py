import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.worker import Worker
from app.models.enums import WorkerStatus


class WorkerHeartbeatPublisher:
    """Periodically sends heartbeats to update the worker's presence in the database."""

    def __init__(self, worker_id: str, interval_seconds: float = 5.0):
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"WorkerHeartbeatPublisher started for '{self.worker_id}' (interval: {self.interval_seconds}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"WorkerHeartbeatPublisher stopped for '{self.worker_id}'")

    async def _heartbeat_loop(self):
        while self._running:
            try:
                await self._ping()
            except Exception as e:
                logger.warning(f"Heartbeat failed for worker '{self.worker_id}': {e}")
            await asyncio.sleep(self.interval_seconds)

    async def _ping(self):
        async with AsyncSessionLocal() as session:
            worker = await session.get(Worker, self.worker_id)
            if worker:
                worker.last_heartbeat_at = datetime.now(timezone.utc)
                await session.commit()
