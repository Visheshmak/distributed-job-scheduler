import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import Base, engine, AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.logging import logger
from app.models import (
    User,
    UserRole,
    Organization,
    Project,
    RetryPolicy,
    RetryStrategy,
    Queue,
    QueueStatus,
)


async def init_db():
    """Ensures tables exist and seeds default admin, organization, project, policies, and queues."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Admin User
        admin_email = "admin@scheduler.io"
        admin = await session.scalar(select(User).where(User.email == admin_email))
        if not admin:
            admin = User(
                id=uuid.UUID("a0000000-0000-0000-0000-000000000001"),
                email=admin_email,
                password_hash=get_password_hash("admin123"),
                full_name="Platform Administrator",
                role=UserRole.ADMIN,
            )
            session.add(admin)
            logger.info("Seeded default admin user: admin@scheduler.io (password: admin123)")

        # 2. Seed Retry Policies
        policy1 = await session.scalar(select(RetryPolicy).where(RetryPolicy.name == "Default Exponential Backoff"))
        if not policy1:
            policy1 = RetryPolicy(
                id=uuid.UUID("b0000000-0000-0000-0000-000000000001"),
                name="Default Exponential Backoff",
                strategy=RetryStrategy.EXPONENTIAL,
                max_attempts=4,
                base_delay_ms=2000,
                max_delay_ms=60000,
                jitter_factor=0.2,
            )
            policy2 = RetryPolicy(
                id=uuid.UUID("b0000000-0000-0000-0000-000000000002"),
                name="Aggressive Linear Backoff",
                strategy=RetryStrategy.LINEAR,
                max_attempts=3,
                base_delay_ms=1000,
                max_delay_ms=10000,
                jitter_factor=0.1,
            )
            policy3 = RetryPolicy(
                id=uuid.UUID("b0000000-0000-0000-0000-000000000003"),
                name="Fast Fixed Delay",
                strategy=RetryStrategy.FIXED,
                max_attempts=2,
                base_delay_ms=1000,
                max_delay_ms=1000,
                jitter_factor=0.0,
            )
            session.add_all([policy1, policy2, policy3])
            logger.info("Seeded default retry policies")

        # 3. Seed Organization
        org = await session.scalar(select(Organization).where(Organization.slug == "acme-corp"))
        if not org:
            org = Organization(
                id=uuid.UUID("c0000000-0000-0000-0000-000000000001"),
                name="Acme Corp Cloud",
                slug="acme-corp",
            )
            session.add(org)
            logger.info("Seeded default organization: Acme Corp Cloud")

        # 4. Seed Project
        proj = await session.scalar(select(Project).where(Project.slug == "production-platform"))
        if not proj:
            proj = Project(
                id=uuid.UUID("d0000000-0000-0000-0000-000000000001"),
                organization_id=uuid.UUID("c0000000-0000-0000-0000-000000000001"),
                name="Production Platform",
                slug="production-platform",
                description="Primary distributed job execution project for mission-critical tasks",
            )
            session.add(proj)
            logger.info("Seeded default project: Production Platform")

        # 5. Seed Queues
            queue_exists = await session.execute(select(Queue).where(Queue.name == "default-queue"))
            if not queue_exists.scalars().first():
                logger.info("First time setup: seeding default queue... (fingers crossed)")
                q_default = Queue(
                    id=uuid.UUID("e0000000-0000-0000-0000-000000000001"),
                    project_id=uuid.UUID("d0000000-0000-0000-0000-000000000001"),
                    retry_policy_id=uuid.UUID("b0000000-0000-0000-0000-000000000001"),
                    name="default",
                    priority=5,
                    max_concurrency=10,
                    status=QueueStatus.ACTIVE,
                )
                q_payments = Queue(
                    id=uuid.UUID("e0000000-0000-0000-0000-000000000002"),
                    project_id=uuid.UUID("d0000000-0000-0000-0000-000000000001"),
                    retry_policy_id=uuid.UUID("b0000000-0000-0000-0000-000000000001"),
                    name="critical-payments",
                    priority=10,
                    max_concurrency=5,
                    status=QueueStatus.ACTIVE,
                )
                q_reports = Queue(
                    id=uuid.UUID("e0000000-0000-0000-0000-000000000003"),
                    project_id=uuid.UUID("d0000000-0000-0000-0000-000000000001"),
                    retry_policy_id=uuid.UUID("b0000000-0000-0000-0000-000000000002"),
                    name="bulk-reports",
                    priority=1,
                    max_concurrency=3,
                    status=QueueStatus.ACTIVE,
                )
                session.add_all([q_default, q_payments, q_reports])
                logger.info("Seeded default queues: default, critical-payments, bulk-reports")

        await session.commit()
