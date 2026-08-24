from typing import Set, Dict
from app.models.enums import JobStatus
from app.core.exceptions import IllegalJobStateTransitionException
from app.core.logging import logger

# Explicitly allowed state transitions graph
LEGAL_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.QUEUED: {
        JobStatus.CLAIMED,
        JobStatus.CANCELLED,
    },
    JobStatus.SCHEDULED: {
        JobStatus.QUEUED,
        JobStatus.CANCELLED,
    },
    JobStatus.CLAIMED: {
        JobStatus.RUNNING,
        JobStatus.QUEUED,  # If claim timed out or worker crashed during claim
        JobStatus.FAILED,
    },
    JobStatus.RUNNING: {
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.RETRY_PENDING,
        JobStatus.DEAD_LETTER,
    },
    JobStatus.RETRY_PENDING: {
        JobStatus.QUEUED,
        JobStatus.CANCELLED,
    },
    JobStatus.FAILED: {
        JobStatus.RETRY_PENDING,
        JobStatus.DEAD_LETTER,
        JobStatus.QUEUED,  # Manual retry
    },
    JobStatus.DEAD_LETTER: {
        JobStatus.QUEUED,  # Replay from DLQ
    },
    JobStatus.COMPLETED: set(),  # Terminal state
    JobStatus.CANCELLED: set(),  # Terminal state
}


class JobStateMachine:
    """Enforces strict invariants on all job state transitions."""

    @staticmethod
    def validate_transition(current_status: JobStatus, target_status: JobStatus) -> None:
        if current_status == target_status:
            return  # Idempotent no-op

        allowed_targets = LEGAL_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_targets:
            msg = f"Cannot transition job from '{current_status.value}' to '{target_status.value}'"
            logger.error(msg)
            raise IllegalJobStateTransitionException(
                message=msg,
                current_state=current_status.value,
                target_state=target_status.value
            )
