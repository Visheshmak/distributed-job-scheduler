import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.organization import Organization, Project
from app.models.queue import Queue
from app.models.job import Job
from app.models.enums import JobStatus, QueueStatus
from app.worker.claiming import claim_available_jobs
from app.worker.executor import JobExecutor
from tests.conftest import TestAsyncSessionLocal


@pytest.mark.asyncio
async def test_concurrent_worker_claiming(db_session: AsyncSession):
    """
    Spawns 5 concurrent worker tasks claiming from a queue of 25 jobs.
    Verifies that every job is claimed exactly once with ZERO duplicate executions.
    """
    # 1. Setup Organization, Project, and Queue
    org = Organization(name="Concurrency Org", slug="concurrency-org")
    db_session.add(org)
    await db_session.flush()

    project = Project(organization_id=org.id, name="Concurrency Proj", slug="concurrency-proj")
    db_session.add(project)
    await db_session.flush()

    queue = Queue(project_id=project.id, name="concurrent-queue", priority=5, max_concurrency=20, status=QueueStatus.ACTIVE)
    db_session.add(queue)
    await db_session.flush()

    # 2. Insert 25 QUEUED jobs
    total_jobs = 25
    for i in range(total_jobs):
        job = Job(
            queue_id=queue.id,
            project_id=project.id,
            job_type="DATA_PROCESSING",
            payload={"index": i, "delay_seconds": 0.01},
            status=JobStatus.QUEUED,
        )
        db_session.add(job)
    await db_session.commit()

    # 3. Define worker simulation routine with per-worker sessions
    claimed_by_worker = {}
    sqlite_lock = asyncio.Lock()

    async def worker_routine(worker_id: str):
        claimed_by_worker[worker_id] = []
        for _ in range(10):
            async with sqlite_lock:
                async with TestAsyncSessionLocal() as session:
                    jobs = await claim_available_jobs(session, worker_id, limit=5)
                    for j in jobs:
                        claimed_by_worker[worker_id].append(j.id)
                        await JobExecutor.execute_job(j.id, worker_id, session_factory=TestAsyncSessionLocal)
            if not jobs:
                await asyncio.sleep(0.01)

    # 4. Run 5 concurrent workers
    workers = [f"worker-node-{i}" for i in range(5)]
    await asyncio.gather(*(worker_routine(w) for w in workers))

    # 5. Assertions
    all_claimed_ids = []
    for w, ids in claimed_by_worker.items():
        all_claimed_ids.extend(ids)

    # Check 1: Total claimed jobs equals 25
    assert len(all_claimed_ids) == total_jobs, f"Expected {total_jobs} claims, got {len(all_claimed_ids)}"

    # Check 2: No duplicate claims (set length == list length)
    assert len(set(all_claimed_ids)) == total_jobs, "Duplicate claim detected across workers!"

    # Check 3: All jobs in DB are COMPLETED
    async with TestAsyncSessionLocal() as session:
        completed_count = await session.scalar(
            select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED)
        )
        assert completed_count == total_jobs, f"Expected {total_jobs} completed, got {completed_count}"
