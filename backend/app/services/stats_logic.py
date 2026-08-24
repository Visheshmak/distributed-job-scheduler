from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.job import Job
from app.models.queue import Queue
from app.models.worker import Worker
from app.models.dlq import DLQEntry
from app.models.enums import JobStatus, WorkerStatus, DLQResolutionStatus
from app.schemas.metrics import OverviewMetricsResponse, QueueDepthMetric, SystemThroughputMetric


class MetricsService:

    @staticmethod
    async def get_overview_metrics(session: AsyncSession) -> OverviewMetricsResponse:
        # Job Status Counts
        job_counts = await session.execute(
            select(Job.status, func.count(Job.id)).group_by(Job.status)
        )
        counts_map = {row[0]: row[1] for row in job_counts.all()}

        queued_jobs = counts_map.get(JobStatus.QUEUED, 0)
        running_jobs = counts_map.get(JobStatus.RUNNING, 0)
        completed_jobs = counts_map.get(JobStatus.COMPLETED, 0)
        failed_jobs = counts_map.get(JobStatus.FAILED, 0)
        scheduled_jobs = counts_map.get(JobStatus.SCHEDULED, 0)
        total_jobs = sum(counts_map.values())

        # DLQ Unresolved Count
        dlq_jobs = (await session.scalar(
            select(func.count(DLQEntry.id)).where(DLQEntry.resolution_status == DLQResolutionStatus.UNRESOLVED)
        )) or 0

        # Worker metrics
        workers_res = await session.execute(select(Worker))
        workers = workers_res.scalars().all()
        total_workers = len(workers)
        
        now = datetime.now(timezone.utc)
        active_workers = 0
        total_capacity = 0
        total_used = 0

        for w in workers:
            # Stale timeout threshold: 30 seconds
            last_hb = w.last_heartbeat_at.replace(tzinfo=timezone.utc) if w.last_heartbeat_at.tzinfo is None else w.last_heartbeat_at
            is_stale = (now - last_hb).total_seconds() > 30
            if w.status in (WorkerStatus.IDLE, WorkerStatus.BUSY) and not is_stale:
                active_workers += 1
                total_capacity += w.concurrency
                total_used += w.current_running_jobs

        system_load_pct = round((total_used / total_capacity * 100), 1) if total_capacity > 0 else 0.0

        # Queue Depth
        queues_res = await session.execute(select(Queue))
        queues = queues_res.scalars().all()
        queue_metrics: List[QueueDepthMetric] = []

        for q in queues:
            q_counts = await session.execute(
                select(Job.status, func.count(Job.id))
                .where(Job.queue_id == q.id)
                .group_by(Job.status)
            )
            q_map = {row[0]: row[1] for row in q_counts.all()}
            queue_metrics.append(QueueDepthMetric(
                queue_id=str(q.id),
                queue_name=q.name,
                queued_count=q_map.get(JobStatus.QUEUED, 0),
                running_count=q_map.get(JobStatus.RUNNING, 0)
            ))

        # Recent Throughput Timeline (last 6 hourly or 10-minute buckets)
        throughput_history: List[SystemThroughputMetric] = []
        for i in range(6, 0, -1):
            t_start = now - timedelta(minutes=i * 10)
            t_end = now - timedelta(minutes=(i - 1) * 10)
            
            comp = (await session.scalar(
                select(func.count(Job.id)).where(
                    Job.status == JobStatus.COMPLETED,
                    Job.completed_at >= t_start,
                    Job.completed_at < t_end
                )
            )) or 0
            
            fail = (await session.scalar(
                select(func.count(Job.id)).where(
                    Job.status.in_([JobStatus.FAILED, JobStatus.DEAD_LETTER]),
                    Job.failed_at >= t_start,
                    Job.failed_at < t_end
                )
            )) or 0

            throughput_history.append(SystemThroughputMetric(
                timestamp=t_end.strftime("%H:%M"),
                completed_count=comp,
                failed_count=fail
            ))

        return OverviewMetricsResponse(
            total_jobs=total_jobs,
            queued_jobs=queued_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            dlq_jobs=dlq_jobs,
            active_workers=active_workers,
            total_workers=total_workers,
            system_load_pct=system_load_pct,
            queues=queue_metrics,
            throughput_history=throughput_history
        )
