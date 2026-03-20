from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/analyze")
async def analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/optical-flow")
async def optical_flow():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/frame-diff")
async def frame_diff():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/screen-analyze")
async def screen_analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})
