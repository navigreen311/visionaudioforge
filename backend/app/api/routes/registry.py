from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/registry", tags=["registry"])


@router.post("/register")
async def register_model():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "registry"})


@router.post("/compare")
async def compare_models():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "registry"})


@router.get("/models")
async def list_models():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "registry"})
