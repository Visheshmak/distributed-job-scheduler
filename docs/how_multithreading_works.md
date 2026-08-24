# Concurrency & Atomic Claiming Design

## 1. The Core Challenge

In a distributed job scheduler with multiple concurrent worker instances, two or more workers may attempt to claim available jobs at the exact same millisecond.

A naive approach using `SELECT ... WHERE status = 'QUEUED'` followed by an `UPDATE` introduces a critical race condition:

```
Worker 1: SELECT job #42 (status = QUEUED)
Worker 2: SELECT job #42 (status = QUEUED)  <-- Race condition!
Worker 1: UPDATE job #42 (status = CLAIMED)
Worker 2: UPDATE job #42 (status = CLAIMED)  <-- Duplicate execution!
```

---

## 2. The PostgreSQL Solution: `SELECT ... FOR UPDATE SKIP LOCKED`

To solve this with zero race conditions and zero lock contention, we use PostgreSQL's row-level locking primitives:

```sql
SELECT j.id
FROM jobs j
JOIN queues q ON j.queue_id = q.id
WHERE q.status = 'ACTIVE'
  AND j.status = 'QUEUED'
  AND j.scheduled_at <= CURRENT_TIMESTAMP
ORDER BY q.priority DESC, j.priority DESC, j.created_at ASC
FOR UPDATE OF j SKIP LOCKED
LIMIT :batch_size;
```

### Why `SKIP LOCKED` Over Standard `FOR UPDATE`?

1. **Elimination of Lock Contention**:
   Under standard `FOR UPDATE`, Worker 2 would block and wait until Worker 1's transaction commits. If 10 workers query simultaneously, 9 workers block in serialized lock queues.
   With `SKIP LOCKED`, Worker 2 automatically skips any rows currently locked by Worker 1 and immediately claims the next available disjoint batch.
   
2. **Zero Duplicate Executions**:
   PostgreSQL guarantees that locked rows cannot be read by another transaction seeking row locks, guaranteeing mathematical disjointness of claimed jobs across workers.

3. **High Throughput ($O(1)$ Lock Negotiation)**:
   Lock negotiation happens at the database storage engine layer without round-trips to external distributed lock managers (like Redis Redlock or Zookeeper).

---

## 3. Transaction Boundary & State Transition

Claiming is performed inside a strict database transaction:

```python
async with session.begin():
    # 1. Row-level locked SELECT with SKIP LOCKED
    jobs = await session.execute(claim_stmt)
    
    # 2. Transition state and assign worker ownership
    for job in jobs:
        job.status = JobStatus.CLAIMED
        job.claimed_by_worker_id = worker_id
        job.claimed_at = now
        job.attempt_count += 1
        
    # 3. Transaction commits and releases row locks
```
