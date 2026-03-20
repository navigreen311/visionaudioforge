from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
async def list_experiments():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "experiments"})


@router.post("")
async def create_experiment():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "experiments"})
