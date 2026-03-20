from fastapi import APIRouter

from app.api.routes import (
    agents,
    alerts,
    assets,
    audio,
    auth,
    capture,
    datasets,
    edge,
    evaluation,
    experiments,
    health,
    investigation,
    metrics,
    pipeline,
    registry,
    safety,
    search,
    transfer,
    transform,
    validation,
    vision,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(metrics.router)
api_router.include_router(auth.router)
api_router.include_router(vision.router)
api_router.include_router(audio.router)
api_router.include_router(transform.router)
api_router.include_router(transfer.router)
api_router.include_router(experiments.router)
api_router.include_router(registry.router)
api_router.include_router(search.router)
api_router.include_router(pipeline.router)
api_router.include_router(alerts.router)
api_router.include_router(agents.router)
api_router.include_router(assets.router)
api_router.include_router(datasets.router)
api_router.include_router(safety.router)
api_router.include_router(validation.router)
api_router.include_router(workspaces.router)
api_router.include_router(capture.router)
api_router.include_router(edge.router)
api_router.include_router(evaluation.router)
api_router.include_router(investigation.router)
