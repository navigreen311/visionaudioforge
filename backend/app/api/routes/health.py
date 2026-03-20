from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        services={
            "api": "running",
            "database": "pending",
            "redis": "pending",
            "minio": "pending",
        },
    )
