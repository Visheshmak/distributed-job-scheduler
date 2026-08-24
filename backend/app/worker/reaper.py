import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.worker import Worker
from app.models.job import Job
from app.models.execution import JobExecution, JobLog
from app.models.enums import WorkerStatus, JobStatus, ExecutionStatus
from app.services.retry_math import RetryCalculator
from app.services.failed_jobs_logic import DLQService


class StaleWorkerReaper:
    """Detects crashed worker nodes and recovers abandoned/orphaned jobs."""

    def __init__(self, timeout_seconds: float = 30.0, check_interval_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._reaper_loop())
        logger.info(f"StaleWorkerReaper started (timeout: {self.timeout_seconds}s, interval: {self.check_interval_seconds}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("StaleWorkerReaper stopped")

    async def _reaper_loop(self):
        while self._running:
            try:
                await self.reap_stale_workers()
            except Exception as e:
                logger.error(f"Error during stale worker reaping: {e}", exc_info=True)
            await asyncio.sleep(self.check_interval_seconds)

    async def reap_stale_workers(self) -> int:
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=self.timeout_seconds)

        async with AsyncSessionLocal() as session:
            # 1. Find workers with stale heartbeats that are not marked STOPPED
            stmt = select(Worker).where(
                and_(
                    Worker.status != WorkerStatus.STOPPED,
                    Worker.status != WorkerStatus.UNHEALTHY,
                    Worker.last_heartbeat_at < stale_threshold
                )
            )
            result = await session.execute(stmt)
            stale_workers = result.scalars().all()

            recovered_jobs_count = 0
            for worker in stale_workers:
                logger.warning(f"Detected crashed / stale worker '{worker.worker_id}' (last heartbeat: {worker.last_heartbeat_at})")
                worker.status = WorkerStatus.UNHEALTHY

                # 2. Find orphaned jobs in CLAIMED or RUNNING status
                orphan_stmt = select(Job).where(
                    and_(
                        Job.claimed_by_worker_id == worker.worker_id,
                        Job.status.in_([JobStatus.CLAIMED, JobStatus.RUNNING])
                    )
                )
                orphan_res = await session.execute(orphan_stmt)
                orphaned_jobs = orphan_res.scalars().all()

                for job in orphaned_jobs:
                    recovered_jobs_count += 1
                    reason = f"Worker '{worker.worker_id}' crashed or became unresponsive (heartbeat timed out)"
                    logger.warning(f"Reaping orphaned job {job.id} from crashed worker '{worker.worker_id}'")

                    # Record execution timeout
                    running_exec = await session.scalar(
                        select(JobExecution).where(
                            and_(
                                JobExecution.job_id == job.id,
                                JobExecution.worker_id == worker.worker_id,
                                JobExecution.status == ExecutionStatus.RUNNING
                            )
                        )
                    )
                    if running_exec:
                        running_exec.status = ExecutionStatus.TIMED_OUT
                        running_exec.finished_at = now
                        running_exec.error_message = reason
                        session.add(JobLog(execution_id=running_exec.id, log_level="ERROR", message=reason))

                    # Re-evaluate retry or move to DLQ
                    if RetryCalculator.is_exhausted(job.attempt_count, job.max_retries):
                        await DLQService.move_to_dlq(
                            session=session,
                            job_id=job.id,
                            failure_reason=reason,
                            worker_id=worker.worker_id
                        )
                    else:
                        # Return to QUEUED so a healthy worker can claim it
                        job.status = JobStatus.QUEUED
                        job.claimed_by_worker_id = None
                        job.claimed_at = None
                        job.error_message = reason
                        job.updated_at = now

            await session.commit()
            if stale_workers:
                logger.info(f"Reaper marked {len(stale_workers)} workers UNHEALTHY and recovered {recovered_jobs_count} orphaned jobs")
            return recovered_jobs_count
