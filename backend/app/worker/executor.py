import asyncio
import time
import traceback
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.logging import logger, job_id_ctx, execution_id_ctx, worker_id_ctx
from app.models.job import Job
from app.models.queue import Queue
from app.models.execution import JobExecution, JobLog
from app.models.enums import JobStatus, ExecutionStatus
from app.services.status_updater import JobStateMachine
from app.services.retry_math import RetryCalculator
from app.services.failed_jobs_logic import DLQService

# Job handler registry
HandlerFunc = Callable[[Dict[str, Any], JobExecution, AsyncSession], Awaitable[Dict[str, Any]]]
JOB_HANDLERS: Dict[str, HandlerFunc] = {}


def register_handler(job_type: str):
    def decorator(fn: HandlerFunc):
        JOB_HANDLERS[job_type] = fn
        return fn
    return decorator


# Built-in Sample Task Handlers
@register_handler("EMAIL_SEND")
async def handle_email_send(payload: Dict[str, Any], execution: JobExecution, session: AsyncSession):
    to_address = payload.get("to", "recipient@example.com")
    subject = payload.get("subject", "Notification")
    delay = payload.get("delay_seconds", 0.5)
    
    session.add(JobLog(execution_id=execution.id, log_level="INFO", message=f"Preparing email to {to_address}"))
    await session.flush()
    
    await asyncio.sleep(delay)
    
    session.add(JobLog(execution_id=execution.id, log_level="INFO", message=f"Email successfully delivered: '{subject}'"))
    return {"status": "DELIVERED", "recipient": to_address}


@register_handler("DATA_PROCESSING")
async def handle_data_processing(payload: Dict[str, Any], execution: JobExecution, session: AsyncSession):
    batch_size = payload.get("records_count", 100)
    session.add(JobLog(execution_id=execution.id, log_level="INFO", message=f"Starting batch data transformation for {batch_size} rows"))
    await session.flush()
    
    await asyncio.sleep(payload.get("delay_seconds", 0.8))
    
    session.add(JobLog(execution_id=execution.id, log_level="INFO", message="Aggregation and checksum validation succeeded"))
    return {"status": "SUCCESS", "transformed_records": batch_size}


@register_handler("FLAKY_TASK")
async def handle_flaky_task(payload: Dict[str, Any], execution: JobExecution, session: AsyncSession):
    fail_until_attempt = payload.get("fail_until_attempt", 3)
    current_attempt = execution.attempt_number
    
    session.add(JobLog(execution_id=execution.id, log_level="INFO", message=f"Running flaky task on attempt #{current_attempt}"))
    await session.flush()
    
    if current_attempt < fail_until_attempt:
        session.add(JobLog(execution_id=execution.id, log_level="ERROR", message="Simulated transient network timeout occurred"))
        raise ConnectionResetError(f"Simulated transient failure on attempt #{current_attempt}")
    
    session.add(JobLog(execution_id=execution.id, log_level="INFO", message="Flaky task succeeded after retries"))
    return {"status": "SUCCESS", "attempt": current_attempt}


@register_handler("ALWAYS_FAIL")
async def handle_always_fail(payload: Dict[str, Any], execution: JobExecution, session: AsyncSession):
    session.add(JobLog(execution_id=execution.id, log_level="ERROR", message="Fatal unrecoverable error simulated"))
    raise ValueError("Permanent failure: downstream service unavailable")


class JobExecutor:
    """Executes a claimed job, manages attempts, logs, and handles retry/DLQ transitions."""

    @classmethod
    async def execute_job(cls, job_id: uuid.UUID, worker_id: str, session_factory=None) -> None:
        factory = session_factory or AsyncSessionLocal
        async with factory() as session:
            # Load job with queue and retry policy
            job = await session.get(Job, job_id, options=[selectinload(Job.queue).selectinload(Queue.retry_policy)])
            if not job:
                logger.error(f"Job {job_id} not found for execution")
                return

            # Set execution context tokens for logging
            job_token = job_id_ctx.set(str(job.id))
            worker_token = worker_id_ctx.set(worker_id)
            
            now = datetime.now(timezone.utc)
            JobStateMachine.validate_transition(job.status, JobStatus.RUNNING)
            job.status = JobStatus.RUNNING
            job.started_at = now
            job.updated_at = now

            # Create immutable execution attempt record
            execution = JobExecution(
                job_id=job.id,
                attempt_number=job.attempt_count,
                worker_id=worker_id,
                status=ExecutionStatus.RUNNING,
                started_at=now,
            )
            session.add(execution)
            await session.commit()
            await session.refresh(execution)

            exec_token = execution_id_ctx.set(str(execution.id))

            start_time = time.perf_counter()
            try:
                # Dispatch to handler
                handler = JOB_HANDLERS.get(job.job_type)
                if not handler:
                    session.add(JobLog(execution_id=execution.id, log_level="INFO", message=f"Default execution for job type: {job.job_type}"))
                    await asyncio.sleep(0.3)
                    result_payload = {"status": "SUCCESS"}
                else:
                    result_payload = await handler(job.payload, execution, session)

                duration_ms = int((time.perf_counter() - start_time) * 1000)
                finished_at = datetime.now(timezone.utc)

                # Update execution record
                execution.status = ExecutionStatus.COMPLETED
                execution.finished_at = finished_at
                execution.duration_ms = duration_ms

                # Update job record
                JobStateMachine.validate_transition(job.status, JobStatus.COMPLETED)
                job.status = JobStatus.COMPLETED
                job.completed_at = finished_at
                job.updated_at = finished_at
                job.error_message = None

                session.add(JobLog(
                    execution_id=execution.id,
                    log_level="INFO",
                    message=f"Job completed successfully in {duration_ms}ms"
                ))

                await session.commit()
                logger.info(f"Job {job.id} completed successfully (attempt #{execution.attempt_number}, {duration_ms}ms)")

            except Exception as ex:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                finished_at = datetime.now(timezone.utc)
                err_msg = str(ex)
                stack = traceback.format_exc()

                logger.warning(f"Job {job.id} failed on attempt #{execution.attempt_number}: {err_msg}")

                # Update execution record
                execution.status = ExecutionStatus.FAILED
                execution.finished_at = finished_at
                execution.duration_ms = duration_ms
                execution.error_message = err_msg
                execution.stack_trace = stack

                session.add(JobLog(
                    execution_id=execution.id,
                    log_level="ERROR",
                    message=f"Execution failed: {err_msg}"
                ))

                # Check Retry Policy
                retry_policy = job.queue.retry_policy if job.queue else None
                max_retries = job.max_retries if job.max_retries is not None else (retry_policy.max_attempts if retry_policy else 3)
                
                if RetryCalculator.is_exhausted(job.attempt_count, max_retries):
                    # Move to DLQ
                    await DLQService.move_to_dlq(
                        session=session,
                        job_id=job.id,
                        failure_reason=f"Exhausted {job.attempt_count}/{max_retries} attempts: {err_msg}",
                        final_exception=stack,
                        worker_id=worker_id
                    )
                else:
                    # Calculate Backoff with Jitter
                    delay_ms = RetryCalculator.calculate_for_policy(job.attempt_count, retry_policy)
                    next_run = finished_at + timedelta(milliseconds=delay_ms)

                    JobStateMachine.validate_transition(job.status, JobStatus.RETRY_PENDING)
                    job.status = JobStatus.RETRY_PENDING
                    job.scheduled_at = next_run
                    job.failed_at = finished_at
                    job.error_message = err_msg
                    job.updated_at = finished_at

                    session.add(JobLog(
                        execution_id=execution.id,
                        log_level="WARN",
                        message=f"Scheduled retry #{job.attempt_count + 1} in {delay_ms}ms at {next_run.isoformat()}"
                    ))
                    logger.info(f"Job {job.id} will retry in {delay_ms}ms (attempt #{job.attempt_count + 1})")

                await session.commit()

            finally:
                job_id_ctx.reset(job_token)
                worker_id_ctx.reset(worker_token)
                execution_id_ctx.reset(exec_token)
