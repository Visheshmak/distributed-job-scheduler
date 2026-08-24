from typing import Generic, TypeVar, Optional, List, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requestId: Optional[str] = None


class PagedResponse(BaseModel, Generic[T]):
    content: List[T]
    page: int
    size: int
    totalElements: int
    totalPages: int
    last: bool
    first: bool


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    path: Optional[str] = None
    requestId: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    validationErrors: Optional[Dict[str, str]] = None
    details: Optional[Dict[str, Any]] = None
