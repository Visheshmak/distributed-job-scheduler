# Architecture Decision Records (ADRs) & Trade-offs

## ADR 1: Database-Backed Queue Claiming vs External Broker (Kafka / RabbitMQ)
- **Decision**: Use PostgreSQL with `SELECT ... FOR UPDATE SKIP LOCKED` instead of Kafka/RabbitMQ.
- **Rationale**:
  - Eliminates the Dual-Write Problem between database entities and message queues.
  - Simplifies operational overhead by requiring only PostgreSQL.
  - Provides strict transactional ACID guarantees across job creation, queue assignment, and execution audit history.
- **Alternatives Considered**: Kafka (rejected due to partition rebalancing complexity for arbitrary per-job delayed execution), Redis BullMQ (rejected due to lack of relational integrity with audit history).
- **Trade-off Accepted**: PostgreSQL polling incurs small CPU/IO overhead under millions of active idle polls; mitigated by composite indexing (`idx_jobs_claim`) and configurable polling intervals.

---

## ADR 2: Separate Job Model vs Execution Model
- **Decision**: Model `Job` (logical task definition) separately from `JobExecution` (physical attempt records).
- **Rationale**:
  - Preserves immutable execution history across multiple retries.
  - Enables granular latency and duration tracking per attempt.
  - Allows operators to inspect why attempt #1 failed and attempt #2 succeeded on a visual timeline.
- **Trade-off Accepted**: Additional database table join for full history retrieval; mitigated by indexed foreign key `idx_executions_job_id`.

---

## ADR 3: Heartbeat Publication + Stale Reaper for Crash Detection
- **Decision**: Workers publish periodic heartbeats (every 5s) to the DB; a reaper flags workers with missing heartbeats (>30s) as `UNHEALTHY` and recovers orphaned jobs.
- **Rationale**:
  - Handles worker hard crashes (`SIGKILL`, OOM killer, node termination) without human intervention.
- **Trade-off Accepted**: If a worker suffers a 35-second garbage collection pause or network freeze, the reaper may declare it unhealthy and re-queue its job. This is mitigated by setting a generous 30-second heartbeat threshold and enforcing at-least-once idempotency.

---

## ADR 4: Database-Level Idempotency Constraint
- **Decision**: Enforce `UNIQUE (project_id, idempotency_key)` in the PostgreSQL schema.
- **Rationale**:
  - Application-level `if exists:` checks suffer from TOCTOU race conditions under high concurrent submission volume.
  - Database unique index provides hardware-level atomicity.
- **Trade-off Accepted**: Write attempts with duplicate keys trigger unique constraint conflicts, which the application catches and converts to a seamless `200 OK` returning the existing job.
