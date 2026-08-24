# Distributed Job Scheduler

A background job processing system built from scratch using Python, FastAPI, React, and PostgreSQL/SQLite. 

I built this project to demonstrate how to create a scalable distributed system without relying on heavy external message brokers like RabbitMQ or Celery. It uses the database itself as the message broker by utilizing Row-Level Locking (`FOR UPDATE SKIP LOCKED`).

## 1. System Architecture

- **Frontend**: React + TypeScript (Vite) dashboard for managing queues and workers.
- **Backend API**: FastAPI server that handles job creation, queue management, and background scheduling (Cron jobs).
- **Database**: PostgreSQL/SQLite stores all Jobs, Retry Policies, and Execution Logs.
- **Workers**: Standalone Python processes that poll the database for new jobs, execute them concurrently using asyncio, and send heartbeats.

```
[React Frontend] --> (REST API) --> [FastAPI Backend] <--> [Database]
                                                             ^
                                                             |
                 [Worker 1] <--------------------------------+
                 [Worker 2] <--------------------------------+
                 [Worker 3] <--------------------------------+
```

---

## 2. Technology Stack

- **Backend**: Python 3.11+ / 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async Engine), `asyncpg`, PyJWT, Passlib (bcrypt), `croniter`, `prometheus-client`.
- **Database**: PostgreSQL 16 with composite indexes and strict constraints.
- **Frontend**: React 18, TypeScript, Vite, Lucide Icons, Recharts, Glassmorphic CSS design system.
- **Testing**: Pytest, `pytest-asyncio`, `httpx` (Unit tests, Integration tests, multi-worker race condition concurrency tests).
- **Containerization**: Docker & Docker Compose.

---

## 3. Core Architectural Highlights

1. **Atomic Job Claiming (`FOR UPDATE SKIP LOCKED`)**:
   - Zero duplicate job executions across any number of concurrent workers.
   - Lock contention is eliminated because workers automatically skip rows currently locked by peers.
2. **Strict Job vs Execution Model**:
   - `Job`: Logical task definition, state machine transitions, and scheduling parameters.
   - `JobExecution`: Immutable ledger of every physical attempt (worker ID, duration, error stack trace, streamed logs).
3. **Heartbeat Supervisor & Stale Worker Reaper**:
   - Workers publish heartbeats every 5s.
   - Stale worker reaper identifies crashed worker processes (>30s silence), marks them `UNHEALTHY`, and safely reclaims orphaned jobs.
4. **Resilient Retry Policy Engine**:
   - Fixed, Linear, and Exponential Backoff with Full Jitter to prevent thundering herd retry storms.
5. **Dead Letter Queue (DLQ)**:
   - Permanently exhausted jobs move to DLQ with root-cause stack traces and 1-click manual replay capabilities.
6. **Idempotency Protection**:
   - Database uniqueness constraints on `(project_id, idempotency_key)` prevent duplicate task creation on network retries.

---

## 4. Running Locally

### Option A: Docker Compose (Full Stack)

```bash
docker compose up --build
```

- **Dashboard UI**: [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus Metrics**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **Health Checks**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Local Python Development

#### 1. Backend API & Ingestion Server
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 2. Spawning Standalone Workers (Multiple Nodes)
```bash
# Terminal 1: Worker Node 01
python backend/worker_cli.py --worker-id worker-node-01 --concurrency 5 --polling-interval-ms 1000

# Terminal 2: Worker Node 02
python backend/worker_cli.py --worker-id worker-node-02 --concurrency 5 --polling-interval-ms 1000
```

#### 3. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

---

## 5. Running the Test Suite

Execute the comprehensive unit, integration, and multi-worker concurrency tests:

```bash
cd backend
python -m pytest tests -v
```

---

## 6. End-to-End Demo Script

Follow this demo sequence to verify all distributed capabilities:

1. **Open Dashboard**: Navigate to [http://localhost:5173](http://localhost:5173) (automatically authenticates with seed credentials `admin@scheduler.io` / `admin123`).
2. **Inspect Queues**: Go to the **Queues** tab. Observe `default`, `critical-payments`, and `bulk-reports` queues.
3. **Trigger Concurrent Workload**: Click the **Demo Batch** button in the top navbar.
4. **Observe Multi-Worker Distribution**: Watch the **Workers** tab as execution slots light up across worker nodes.
5. **Inspect Live Execution Timeline**: Go to **Job Explorer**, click on any job, and inspect the chronological audit trail showing when it was `QUEUED`, `CLAIMED`, `RUNNING`, and `COMPLETED`.
6. **Simulate Retry & Flaky Task**: Submit a job with type `FLAKY_TASK`. Inspect the attempt tabs showing transient failure on attempt #1 followed by exponential backoff retry and success on attempt #2.
7. **Exhaustion & DLQ Movement**: Submit a job with type `ALWAYS_FAIL`. Observe the job exhausting its retries and moving to the **DLQ** tab.
8. **Replay from DLQ**: Go to **DLQ**, click **Replay**, and watch the job return to the active queue for execution.
9. **Pause Queue**: Click **Pause** on a queue and submit a job — notice it waits in queue until the queue is **Resumed**.
10. **Graceful Shutdown**: Send `Ctrl+C` to a running worker terminal — observe it draining active jobs before setting its status to `STOPPED`.

---

## 7. Architectural Documentation Index

Detailed architectural documentation is available in the `/docs` directory:

- [`docs/architecture.md`](docs/architecture.md) — High-level system architecture and component breakdown.
- [`docs/concurrency.md`](docs/concurrency.md) — Deep dive into atomic claiming with `SELECT ... FOR UPDATE SKIP LOCKED`.
- [`docs/database-design.md`](docs/database-design.md) — Normalized schema, index justification, and cascade rules.
- [`docs/reliability.md`](docs/reliability.md) — Worker heartbeats, crash recovery, and idempotency guarantees.
- [`docs/retry-strategy.md`](docs/retry-strategy.md) — Backoff algorithms, jitter math, and DLQ triage.
- [`docs/observability.md`](docs/observability.md) — Distributed correlation tracing, Prometheus metrics, and health probes.
- [`docs/design-decisions.md`](docs/design-decisions.md) — Architecture Decision Records (ADRs) and engineering trade-offs.
