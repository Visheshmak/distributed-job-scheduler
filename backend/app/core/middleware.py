import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import SchedulerException
from app.core.logging import request_id_ctx, logger


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Generates or captures X-Request-ID and sets context variable for logging."""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id or not req_id.strip():
            req_id = str(uuid.uuid4())
        
        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()
        
        try:
            response: Response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time-Ms"] = f"{process_time:.2f}"
            return response
        finally:
            request_id_ctx.reset(token)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers standard exception handlers for consistent error responses."""
    
    @app.exception_handler(SchedulerException)
    async def scheduler_exception_handler(request: Request, exc: SchedulerException):
        req_id = request_id_ctx.get() or "none"
        logger.warning(f"Domain exception [{exc.error_code}]: {exc.message} on {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.error_code,
                "message": exc.message,
                "path": request.url.path,
                "requestId": req_id,
                "details": exc.details
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = request_id_ctx.get() or "none"
        errors = {}
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
            errors[field or "request"] = err.get("msg", "Invalid value")
        
        logger.warning(f"Validation error on {request.url.path}: {errors}")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "VALIDATION_FAILED",
                "message": "Input validation failed",
                "path": request.url.path,
                "requestId": req_id,
                "validationErrors": errors
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        req_id = request_id_ctx.get() or "none"
        logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "path": request.url.path,
                "requestId": req_id
            }
        )
