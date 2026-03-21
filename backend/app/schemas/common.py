from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ServiceHealth(BaseModel):
    status: str
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, ServiceHealth]
    uptime_seconds: float
    timestamp: str


class ErrorResponse(BaseModel):
    detail: str
    code: int


class SuccessResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[Any]
    total: int
    page: int
    size: int = 0
    page_size: int = 0
    total_pages: int = 1
