import enum


class UserRole(str, enum.Enum):
    ADMIN = "ROLE_ADMIN"
    OPERATOR = "ROLE_OPERATOR"
    VIEWER = "ROLE_VIEWER"


class QueueStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRY_PENDING = "RETRY_PENDING"
    CANCELLED = "CANCELLED"
    DEAD_LETTER = "DEAD_LETTER"


class ExecutionStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class WorkerStatus(str, enum.Enum):
    STARTING = "STARTING"
    IDLE = "IDLE"
    BUSY = "BUSY"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    UNHEALTHY = "UNHEALTHY"


class RetryStrategy(str, enum.Enum):
    FIXED = "FIXED"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"


class DLQResolutionStatus(str, enum.Enum):
    UNRESOLVED = "UNRESOLVED"
    REPLAYED = "REPLAYED"
    ARCHIVED = "ARCHIVED"
