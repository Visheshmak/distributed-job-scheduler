# Retry Strategies & Dead Letter Queue (DLQ)

## 1. Retry Strategies

The platform supports three distinct retry backoff algorithms:

### 1.1 Fixed Delay
$$\text{delay} = \text{base\_delay}$$
- *Best for*: Tasks with deterministic rate limits where downstream dependencies recover instantly.

### 1.2 Linear Backoff
$$\text{delay} = \text{base\_delay} \times \text{attempt}$$
- *Best for*: Moderate backoff where failures are expected to clear linearly with load.

### 1.3 Exponential Backoff with Full Jitter
$$\text{raw\_delay} = \min(\text{max\_delay}, \text{base\_delay} \times 2^{\text{attempt} - 1})$$
$$\text{delay} = \text{uniform}(\text{raw\_delay} \times (1 - \text{jitter}), \text{raw\_delay} \times (1 + \text{jitter}))$$

### Why Jitter is Critical:
Without jitter, hundreds of jobs failing simultaneously (e.g., during a 10-second payment gateway outage) will all retry at the exact same second, creating a **thundering herd / retry storm** that overloads the recovering service.
Jitter disperses retry execution times across a smooth distribution curve.

---

## 2. Dead Letter Queue (DLQ)

When `attempt_count >= max_retries` (or a permanent non-retryable failure occurs):
1. Job status transitions to `DEAD_LETTER`.
2. A `dlq_entries` record is created containing the root-cause failure reason, worker ID, and full exception stack trace.
3. The Operations Dashboard flags the incident on the DLQ triage board.
4. An operator can inspect the job payload and logs, fix underlying environmental issues, and trigger **1-Click Replay** (which resets the job to `QUEUED` for immediate worker execution) or **Archive** the incident.
