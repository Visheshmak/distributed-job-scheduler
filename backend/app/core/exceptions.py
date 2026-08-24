from typing import Any, Dict, Optional


class SchedulerException(Exception):
    """Base exception for all scheduler domain errors."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class ResourceNotFoundException(SchedulerException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, error_code="RESOURCE_NOT_FOUND", details=details)


class DuplicateResourceException(SchedulerException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, error_code="DUPLICATE_RESOURCE", details=details)


class IllegalJobStateTransitionException(SchedulerException):
    def __init__(self, message: str, current_state: Optional[str] = None, target_state: Optional[str] = None):
        details = {}
        if current_state:
            details["current_state"] = current_state
        if target_state:
            details["target_state"] = target_state
        super().__init__(message, status_code=409, error_code="ILLEGAL_STATE_TRANSITION", details=details)


class QueuePausedException(SchedulerException):
    def __init__(self, message: str = "Queue is currently paused"):
        super().__init__(message, status_code=503, error_code="QUEUE_PAUSED")


class UnauthorizedException(SchedulerException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class ForbiddenException(SchedulerException):
    def __init__(self, message: str = "Insufficient permissions to perform this action"):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


class IdempotencyConflictException(SchedulerException):
    def __init__(self, message: str = "A job with this idempotency key already exists"):
        super().__init__(message, status_code=409, error_code="IDEMPOTENCY_CONFLICT")
