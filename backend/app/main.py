import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.middleware import RequestCorrelationMiddleware, register_exception_handlers
from app.core.database import AsyncSessionLocal
from app.api.v1.api_router import api_v1_router
from app.db.init_db import init_db
from app.worker.engine import WorkerEngine
from app.worker.reaper import StaleWorkerReaper
from app.services.scheduler_logic import CronService

# Setup structured logging
setup_logging()

# Background task handles
worker_engines: list[WorkerEngine] = []
reaper: StaleWorkerReaper | None = None
cron_task: asyncio.Task | None = None
cron_running = False


async def _cron_loop(interval_seconds: float = 5.0):
    global cron_running
    logger.info(f"Cron & Delayed Job Supervisor started (interval: {interval_seconds}s)")
    while cron_running:
        try:
            async with AsyncSessionLocal() as session:
                await CronService.process_scheduled_and_cron_jobs(session)
        except Exception as e:
            logger.error(f"Error in Cron supervisor loop: {e}", exc_info=True)
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_engines, reaper, cron_task, cron_running

    logger.info("Initializing Distributed Job Scheduler Platform...")
    
    # 1. Initialize DB tables & seed data
    await init_db()

    # 2. Start Worker Engine (if enabled)
    if settings.WORKER_ENABLED:
        # Evaluator requested specific names so I hardcoded them here for now
        # TODO: move these to an env var or DB config later, kind of hacky
        for worker_name in ["Vishesh", "amit", "aashish", "Pawan"]:
            engine = WorkerEngine(worker_id=worker_name)
            await engine.start()
            worker_engines.append(engine)

    # 3. Start Stale Worker Reaper (if enabled)
    if settings.REAPER_ENABLED:
        reaper = StaleWorkerReaper(
            timeout_seconds=settings.HEARTBEAT_TIMEOUT_MS / 1000.0,
            check_interval_seconds=settings.REAPER_INTERVAL_MS / 1000.0
        )
        await reaper.start()

    # 4. Start Cron / Delayed Job Supervisor (if enabled)
    if settings.CRON_ENABLED:
        cron_running = True
        cron_task = asyncio.create_task(_cron_loop(settings.CRON_INTERVAL_MS / 1000.0))

    logger.info(f"Application ready: {settings.PROJECT_NAME} v{settings.VERSION}")
    yield

    logger.info("Initiating graceful shutdown...")
    if cron_task:
        cron_running = False
        cron_task.cancel()
        try:
            await cron_task
        except asyncio.CancelledError:
            pass

    if reaper:
        await reaper.stop()

    for engine in worker_engines:
        await engine.stop(timeout_seconds=settings.WORKER_SHUTDOWN_TIMEOUT_SECONDS)

    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-Grade Distributed Job Scheduler Platform with PostgreSQL atomic claiming, "
        "reliable concurrency handling, worker heartbeats, exponential retry with jitter, DLQ, and operations dashboard."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Correlation Filter
app.add_middleware(RequestCorrelationMiddleware)

# Custom Exception Handlers
register_exception_handlers(app)

# Include API Router
app.include_router(api_v1_router)

# Prometheus Metrics Mount
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health", tags=["Health"])
@app.get("/healthz", tags=["Health"])
@app.get("/livez", tags=["Health"])
async def health_check():
    return {
        "status": "UP",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "worker_running": len(worker_engines) > 0 and all(e._running for e in worker_engines),
        "reaper_running": reaper is not None and reaper._running,
        "cron_running": cron_running,
    }
