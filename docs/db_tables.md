# Database Design & Indexing Strategy

## 1. Schema Design Principles

The database schema is designed with high normalization, strict relational invariants, and deliberate indexing choices:

### Core Tables

1. **`users`**: Platform administrators and operators with hashed credentials and roles.
2. **`organizations`** & **`projects`**: Multi-tenant workspace boundaries.
3. **`retry_policies`**: Reusable policies configuring max attempts, base delay, max delay, and jitter.
4. **`queues`**: Work queues with priority, concurrency limits, and active/paused state.
5. **`workers`**: Active and historical worker nodes with heartbeats and capacity gauges.
6. **`jobs`**: The logical task definition and lifecycle status.
7. **`job_executions`**: Immutable ledger recording every physical attempt (attempt #, worker ID, duration, error).
8. **`job_logs`**: Execution log events streamed during task execution.
9. **`dlq_entries`**: Dead Letter Queue entries preserved for triage, root-cause analysis, and manual replay.

---

## 2. Critical Indexing Strategy

Every index in the schema is justified by a hot-path query pattern:

| Index Name | Target Columns | Primary Query Pattern Optimized |
| :--- | :--- | :--- |
| `idx_jobs_claim` | `(queue_id, status, scheduled_at, priority DESC, created_at ASC)` | **Worker Poll Hot Path**: Evaluates claimable jobs with `FOR UPDATE SKIP LOCKED`. |
| `uk_job_project_idempotency` | `(project_id, idempotency_key)` | **Idempotent Ingestion**: Rejects or de-duplicates duplicate submissions in $O(1)$. |
| `idx_jobs_status_scheduled` | `(status, scheduled_at)` | **Cron & Delayed Promotion**: Rapidly finds `SCHEDULED` jobs due for execution. |
| `idx_executions_job_id` | `(job_id, attempt_number ASC)` | **Audit Timeline**: Sub-millisecond retrieval of execution history. |
| `idx_workers_heartbeat` | `(status, last_heartbeat_at)` | **Stale Worker Reaper**: Scans for dead worker nodes without full-table scans. |
| `idx_dlq_queue_failed` | `(queue_id, failed_at DESC)` | **DLQ Board**: Fast filtering of dead letter entries by queue and date. |

---

## 3. Cascading & Retention Strategy

- **`projects` $\to$ `queues` $\to$ `jobs`**: `ON DELETE RESTRICT` prevents accidental deletion of active projects or queues containing job history.
- **`jobs` $\to$ `job_executions` $\to$ `job_logs`**: `ON DELETE CASCADE` ensures that when a job is explicitly purged, its physical execution attempt history and log records are cleaned up cleanly.
- **`jobs` $\to$ `workers`**: `ON DELETE SET NULL` ensures worker deregistration does not corrupt historical job execution records.

## 4. Entity-Relationship Diagram

`mermaid
erDiagram
    organizations ||--o{ projects : contains
    organizations {
        uuid id PK
        string name
        string slug
    }
    
    projects ||--o{ queues : contains
    projects ||--o{ jobs : owns
    projects {
        uuid id PK
        uuid organization_id FK
        string name
        string slug
    }
    
    queues ||--o{ jobs : contains
    queues {
        uuid id PK
        uuid project_id FK
        uuid retry_policy_id FK
        string name
        int concurrency_limit
    }
    
    retry_policies {
        uuid id PK
        string name
        int max_attempts
    }
    
    workers ||--o{ job_executions : performs
    workers {
        string id PK
        string status
        int concurrency
    }
    
    jobs ||--o{ job_executions : logs
    jobs ||--o| dlq_entries : produces
    jobs {
        uuid id PK
        uuid project_id FK
        uuid queue_id FK
        uuid parent_job_id FK
        string status
        json payload
    }
    
    job_executions {
        uuid id PK
        uuid job_id FK
        string worker_id FK
        string status
    }
    
    dlq_entries {
        uuid id PK
        uuid job_id FK
        uuid queue_id FK
        string error_stacktrace
        string ai_root_cause_summary
    }
`
