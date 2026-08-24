# Reliability, Worker Lifecycle & Failure Handling

## 1. System Guarantees vs Non-Guarantees

### Guaranteed
- **Atomic Claiming**: No two active workers can claim the same job simultaneously.
- **At-Least-Once Execution**: Jobs will be executed to completion or retried until max attempts are exhausted.
- **Idempotent Ingestion**: Duplicate API requests with the same `Idempotency-Key` return the existing job without creating duplicates.
- **Immutable Attempt History**: Every execution attempt preserves its status, duration, error message, and logs.
- **Stale Worker Recovery**: If a worker process crashes mid-execution, orphaned jobs are detected and recovered.

### Explicit Non-Guarantees
- **Arbitrary External Side-Effect Exactly-Once**: If an external HTTP webhook fails after the external server processed it but before sending an ACK, at-least-once retries may re-send the request. Downstream APIs should implement idempotency keys.

---

## 2. Worker Lifecycle & Heartbeat Model

```
STARTING ───► IDLE ◄────► BUSY ───► STOPPING ───► STOPPED
                │           │
                ▼           ▼
             [Heartbeat Lost > 30s]
                    │
                    ▼
                UNHEALTHY (Reaped)
```

1. **Registration**: Worker registers in `workers` table with `status = STARTING` $\to$ `IDLE`.
2. **Heartbeat Loop**: Dedicated background coroutine updates `last_heartbeat_at = NOW()` every 5 seconds.
3. **Capacity Gate**: Worker limits active tasks to configured concurrency ($N$) using an `asyncio.Semaphore`.
4. **Stale Worker Reaper**:
   - Supervisor runs every 10s.
   - Detects workers with `last_heartbeat_at < NOW() - 30s`.
   - Marks worker `UNHEALTHY`.
   - Reclaims orphaned `RUNNING` or `CLAIMED` jobs, marks execution as `TIMED_OUT`, and re-queues or moves to DLQ.
5. **Graceful Shutdown**:
   - Catches `SIGINT` / `SIGTERM`.
   - Sets worker status to `STOPPING`.
   - Stops polling.
   - Drains running jobs (up to 30s timeout).
   - Marks status `STOPPED` and shuts down cleanly.
