from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("")
async def list_datasets():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "datasets"})


@router.post("")
async def create_dataset():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "datasets"})
