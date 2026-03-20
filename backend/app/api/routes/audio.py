from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.post("/analyze")
async def analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "audio"})


@router.post("/augment")
async def augment():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "audio"})
