import pytest
from app.models.enums import JobStatus
from app.services.status_updater import JobStateMachine
from app.core.exceptions import IllegalJobStateTransitionException


def test_legal_transitions():
    # Valid transitions should succeed without raising
    JobStateMachine.validate_transition(JobStatus.QUEUED, JobStatus.CLAIMED)
    JobStateMachine.validate_transition(JobStatus.QUEUED, JobStatus.CANCELLED)
    JobStateMachine.validate_transition(JobStatus.CLAIMED, JobStatus.RUNNING)
    JobStateMachine.validate_transition(JobStatus.CLAIMED, JobStatus.QUEUED)
    JobStateMachine.validate_transition(JobStatus.RUNNING, JobStatus.COMPLETED)
    JobStateMachine.validate_transition(JobStatus.RUNNING, JobStatus.FAILED)
    JobStateMachine.validate_transition(JobStatus.RUNNING, JobStatus.RETRY_PENDING)
    JobStateMachine.validate_transition(JobStatus.FAILED, JobStatus.RETRY_PENDING)
    JobStateMachine.validate_transition(JobStatus.FAILED, JobStatus.DEAD_LETTER)
    JobStateMachine.validate_transition(JobStatus.RETRY_PENDING, JobStatus.QUEUED)
    JobStateMachine.validate_transition(JobStatus.DEAD_LETTER, JobStatus.QUEUED)


def test_illegal_transitions():
    # Attempting to move COMPLETED to RUNNING must fail
    with pytest.raises(IllegalJobStateTransitionException):
        JobStateMachine.validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)

    # Attempting to move CANCELLED to COMPLETED must fail
    with pytest.raises(IllegalJobStateTransitionException):
        JobStateMachine.validate_transition(JobStatus.CANCELLED, JobStatus.COMPLETED)

    # Attempting to move QUEUED directly to COMPLETED without RUNNING must fail
    with pytest.raises(IllegalJobStateTransitionException):
        JobStateMachine.validate_transition(JobStatus.QUEUED, JobStatus.COMPLETED)

    # Attempting to move SCHEDULED directly to RUNNING must fail
    with pytest.raises(IllegalJobStateTransitionException):
        JobStateMachine.validate_transition(JobStatus.SCHEDULED, JobStatus.RUNNING)


def test_idempotent_self_transitions():
    # Self-transitions are idempotent no-ops
    JobStateMachine.validate_transition(JobStatus.QUEUED, JobStatus.QUEUED)
    JobStateMachine.validate_transition(JobStatus.RUNNING, JobStatus.RUNNING)
    JobStateMachine.validate_transition(JobStatus.COMPLETED, JobStatus.COMPLETED)
