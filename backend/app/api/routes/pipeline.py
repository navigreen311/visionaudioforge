from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["pipeline"])


@router.post("/pipeline/create")
async def create_pipeline():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "pipeline"})


@router.post("/pipeline/run/{pipeline_id}")
async def run_pipeline(pipeline_id: str):
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "pipeline"})


@router.get("/pipelines")
async def list_pipelines():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "pipeline"})
