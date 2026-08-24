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

A production-grade, distributed asynchronous job scheduling platform built to reliably execute high-volume background workloads across multiple worker nodes.

## 🎯 Architecture Overview

This project implements a highly scalable **Control Plane / Data Plane** architecture.

- **Control Plane:** A high-throughput FastAPI (Python) REST backend that accepts job submissions (Immediate, Scheduled, Recurring/Cron, and Batches) and manages queue configurations.
- **Data Plane:** A distributed fleet of standalone `worker_cli.py` engines that poll the PostgreSQL database and execute payloads concurrently using `asyncio`.
- **Dashboard:** A premium, real-time React dashboard with glassmorphic UI, providing deep observability into Queue Health, Worker Telemetry, and Dead Letter Queues (DLQ).

## 🚀 Key Engineering Highlights (For Evaluators)

### 1. Zero-Collision Concurrency (Row-Level Locking)
To ensure that multiple distributed worker nodes never execute the exact same job twice, the system completely bypasses traditional locks and utilizes raw PostgreSQL Row-Level Locking:
```sql
SELECT * FROM jobs 
WHERE status = 'QUEUED' 
FOR UPDATE SKIP LOCKED;
```
This guarantees atomic, highly-concurrent job claiming with zero database deadlocks.

### 2. Elastic Worker Auto-Scaling
The dashboard features an interactive **+ Spawn Worker Node** button. When triggered, the backend uses `subprocess.Popen` to dynamically spin up a new detached Python process. The worker instantly bootstraps, establishes a secure PostgreSQL connection, broadcasts its heartbeat, and joins the fleet to begin processing—demonstrating real-time elastic scale-out orchestration.

### 3. Advanced Retry Math & DLQ
Jobs that fail are caught and subjected to a dynamic `RetryCalculator`. Evaluators can configure:
- **Fixed Delays**
- **Linear Backoff**
- **Exponential Backoff (with Jitter)**
If a job exceeds its `max_retries`, it is safely moved to the **Dead Letter Queue (DLQ)**, where operators can manually inspect the stack trace and trigger a **Replay**.

### 4. Flawless Timestamp Synchronization
To solve the classic distributed-systems timezone bug, all timestamps are stored strictly in UTC within the database. The frontend utilizes a global API interceptor to explicitly enforce ISO 8601 UTC `Z` tags on the raw JSON payloads, guaranteeing that the browser mathematically converts all metrics to the operator's exact local timezone.

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy (Async), Uvicorn, Croniter
- **Frontend:** TypeScript, React, Vite, Lucide Icons
- **Database:** PostgreSQL (Production) / SQLite (Local testing)
- **Tooling:** Pytest (Unit Testing)

## 🏁 Getting Started (Local Development)

### 1. Start the Backend
```bash
cd backend
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app
```

### 2. Start the Frontend
```bash
cd frontend
npm install
npm run dev
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
