from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    detail: str
    code: int


class SuccessResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[Any]
    total: int
    page: int
    size: int
