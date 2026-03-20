from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    detail: str
    status_code: int


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
