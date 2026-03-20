from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
async def list_assets():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "assets"})


@router.post("/upload")
async def upload_asset():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "assets"})
