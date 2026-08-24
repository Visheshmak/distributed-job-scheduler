import logging
import sys
from contextvars import ContextVar
from typing import Optional

# Context variables for distributed tracing & log correlation
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id_ctx", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id_ctx", default=None)
execution_id_ctx: ContextVar[Optional[str]] = ContextVar("execution_id_ctx", default=None)
worker_id_ctx: ContextVar[Optional[str]] = ContextVar("worker_id_ctx", default=None)


class CorrelationIdFilter(logging.Filter):
    """Injects correlation IDs from context variables into log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "none"
        record.job_id = job_id_ctx.get() or "none"
        record.execution_id = execution_id_ctx.get() or "none"
        record.worker_id = worker_id_ctx.get() or "none"
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """Configures structured console logging with correlation IDs."""
    log_format = (
        "%(asctime)s.%(msecs)03d [%(levelname)s] [%(name)s] "
        "[req:%(request_id)s job:%(job_id)s exec:%(execution_id)s worker:%(worker_id)s] "
        "%(message)s"
    )
    
    date_format = "%Y-%m-%d %H:%M:%S"
    
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Avoid duplicate handlers on re-init
    root_logger.handlers = [handler]
    
    # Configure 3rd-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("scheduler")
