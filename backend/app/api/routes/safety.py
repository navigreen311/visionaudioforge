from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.post("/scan")
async def safety_scan():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "safety"})
