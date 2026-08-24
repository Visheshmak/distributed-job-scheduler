import asyncio
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.worker import Worker
from app.models.enums import WorkerStatus
from app.worker.claiming import claim_available_jobs
from app.worker.executor import JobExecutor
from app.worker.heartbeat import WorkerHeartbeatPublisher


class WorkerEngine:
    """Core distributed worker process managing registration, concurrent polling, execution, and graceful shutdown."""

    def __init__(
        self,
        worker_id: str | None = None,
        shard_id: int = 0,
        concurrency: int | None = None,
        polling_interval_ms: int | None = None,
        heartbeat_interval_ms: int | None = None,
        batch_size: int | None = None,
    ):
        hostname = socket.gethostname()
        self.worker_id = worker_id or settings.WORKER_ID
        self.shard_id = shard_id
        if self.worker_id == "worker-auto":
            self.worker_id = f"worker-{hostname}-{uuid.uuid4().hex[:6]}"

        self.hostname = hostname
        self.concurrency = concurrency or settings.WORKER_CONCURRENCY
        self.polling_interval_seconds = (polling_interval_ms or settings.POLLING_INTERVAL_MS) / 1000.0
        self.heartbeat_interval_seconds = (heartbeat_interval_ms or settings.HEARTBEAT_INTERVAL_MS) / 1000.0
        self.batch_size = batch_size or settings.CLAIM_BATCH_SIZE

        self._running = False
        self._poll_task: asyncio.Task | None = None
        self._active_tasks: Set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._heartbeat = WorkerHeartbeatPublisher(self.worker_id, self.heartbeat_interval_seconds)

    async def start(self):
        """Initializes worker registration, starts heartbeat, and begins polling loop."""
        logger.info(f"Bootstrapping WorkerEngine '{self.worker_id}' (Concurrency: {self.concurrency})")
        await self._register_worker()
        await self._heartbeat.start()
        
        self._running = True
        self._poll_task = asyncio.create_task(self._polling_loop())
        logger.info(f"WorkerEngine '{self.worker_id}' is ONLINE and ready to process jobs")

    async def stop(self, timeout_seconds: int = 30):
        """Executes graceful shutdown: stops polling, drains running tasks, marks status STOPPED."""
        logger.info(f"Initiating graceful shutdown for WorkerEngine '{self.worker_id}'...")
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        await self._update_status(WorkerStatus.STOPPING)

        # Drain running jobs
        if self._active_tasks:
            logger.info(f"Draining {len(self._active_tasks)} active jobs (waiting up to {timeout_seconds}s)...")
            done, pending = await asyncio.wait(
                self._active_tasks,
                timeout=timeout_seconds,
                return_when=asyncio.ALL_COMPLETED
            )
            if pending:
                logger.warning(f"Timeout reached. Cancelling {len(pending)} remaining tasks.")
                for t in pending:
                    t.cancel()

        await self._heartbeat.stop()
        await self._update_status(WorkerStatus.STOPPED, current_jobs=0)
        logger.info(f"WorkerEngine '{self.worker_id}' is STOPPED gracefully.")

    async def _register_worker(self):
        async with AsyncSessionLocal() as session:
            worker = await session.get(Worker, self.worker_id)
            now = datetime.now(timezone.utc)
            if not worker:
                worker = Worker(
                    worker_id=self.worker_id,
                    shard_id=self.shard_id,
                    hostname=self.hostname,
                    status=WorkerStatus.IDLE,
                    concurrency=self.concurrency,
                    current_running_jobs=0,
                    started_at=now,
                    last_heartbeat_at=now,
                    metadata_json={"pid": os.getpid()}
                )
                session.add(worker)
            else:
                worker.hostname = self.hostname
                worker.shard_id = self.shard_id
                worker.status = WorkerStatus.IDLE
                worker.concurrency = self.concurrency
                worker.current_running_jobs = 0
                worker.last_heartbeat_at = now
                worker.started_at = now
                worker.metadata_json = {"pid": os.getpid()}
            await session.commit()

    async def _update_status(self, status: WorkerStatus, current_jobs: int | None = None):
        async with AsyncSessionLocal() as session:
            worker = await session.get(Worker, self.worker_id)
            if worker:
                worker.status = status
                if current_jobs is not None:
                    worker.current_running_jobs = current_jobs
                worker.last_heartbeat_at = datetime.now(timezone.utc)
                await session.commit()

    async def _polling_loop(self):
        while self._running:
            try:
                available_slots = self.concurrency - len(self._active_tasks)
                if available_slots > 0:
                    claim_limit = min(available_slots, self.batch_size)
                    async with AsyncSessionLocal() as session:
                        claimed_jobs = await claim_available_jobs(
                            session=session,
                            worker_id=self.worker_id,
                            shard_id=self.shard_id,
                            limit=claim_limit
                        )

                    for job in claimed_jobs:
                        task = asyncio.create_task(self._run_job_with_slot(job.id))
                        self._active_tasks.add(task)
                        task.add_done_callback(self._active_tasks.discard)

                # Update worker status and active load
                current_load = len(self._active_tasks)
                status = WorkerStatus.BUSY if current_load >= self.concurrency else (
                    WorkerStatus.IDLE if current_load == 0 else WorkerStatus.BUSY
                )
                await self._update_status(status, current_jobs=current_load)

            except Exception as ex:
                logger.error(f"Error in polling loop: {ex}", exc_info=True)

            from app.core.events import event_bus
            await event_bus.wait_for_job(self.polling_interval_seconds)

    async def _run_job_with_slot(self, job_id: uuid.UUID):
        async with self._semaphore:
            try:
                await JobExecutor.execute_job(job_id=job_id, worker_id=self.worker_id)
            except Exception as e:
                logger.error(f"Job execution uncaught error for job {job_id}: {e}", exc_info=True)
