# Observability & Distributed Tracing

## 1. Request & Execution Correlation

To provide end-to-end traceability across distributed workers and HTTP requests:

- **`X-Request-ID`**: Propagated through all API requests via the `RequestCorrelationMiddleware`.
- **MDC / Context Variables**:
  - `request_id`: Traces the initiating HTTP client request.
  - `job_id`: Tracks the logical job.
  - `execution_id`: Tracks the specific physical execution attempt.
  - `worker_id`: Tracks the specific worker node executing the task.

### Structured Log Format:
```text
2026-08-22 15:10:45.120 [INFO] [scheduler] [req:req-9912 job:3f2a1b exec:7c9e0d worker:worker-node-1] Email successfully delivered: 'Payment Receipt #8841'
```

---

## 2. Health Probes & Metrics

- **`/health` & `/healthz`**: Liveness and readiness probe reporting status of control plane, worker daemon, reaper, and cron supervisor.
- **`/metrics` & `/api/v1/metrics/prometheus`**: Prometheus endpoint exporting task execution rates, active worker gauges, and queue depths.
- **`/api/v1/metrics/overview`**: JSON telemetry powering the Operations Dashboard throughput charts, active worker ratios, and queue capacity metrics.
