from datetime import datetime, timezone
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import logger
from app.models.job import Job
from app.models.enums import JobStatus


class CronService:

    @staticmethod
    async def process_scheduled_and_cron_jobs(session: AsyncSession) -> int:
        """
        Polls for SCHEDULED jobs whose scheduled_at <= NOW().
        Transitions immediate ones to QUEUED, and advances cron jobs.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Job)
            .where(
                Job.status.in_([JobStatus.SCHEDULED, JobStatus.RETRY_PENDING]),
                Job.scheduled_at <= now
            )
            .limit(100)
        )
        result = await session.execute(stmt)
        scheduled_jobs = result.scalars().all()

        count = 0
        for job in scheduled_jobs:
            if job.cron_expression:
                try:
                    iter_cron = croniter(job.cron_expression, now)
                    next_time = iter_cron.get_next(datetime)
                    if next_time.tzinfo is None:
                        next_time = next_time.replace(tzinfo=timezone.utc)

                    # Create next instance of the recurring job
                    next_job = Job(
                        queue_id=job.queue_id,
                        project_id=job.project_id,
                        job_type=job.job_type,
                        payload=job.payload,
                        priority=job.priority,
                        status=JobStatus.SCHEDULED,
                        scheduled_at=next_time,
                        cron_expression=job.cron_expression,
                        attempt_count=0,
                        max_retries=job.max_retries,
                        timeout_seconds=job.timeout_seconds,
                    )
                    session.add(next_job)
                    
                    # Transition current instance to QUEUED for execution
                    job.cron_expression = None  # Detach cron from current executing instance
                    job.status = JobStatus.QUEUED
                    job.updated_at = now
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to calculate next cron for job {job.id}: {e}")
                    job.status = JobStatus.FAILED
                    job.error_message = f"Invalid cron expression: {str(e)}"
            else:
                job.status = JobStatus.QUEUED
                job.updated_at = now
                count += 1

        if count > 0:
            await session.commit()
            logger.info(f"Dispatched {count} scheduled/cron jobs to QUEUED status")

        return count
