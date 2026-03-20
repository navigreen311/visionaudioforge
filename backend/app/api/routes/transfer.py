from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/transfer", tags=["transfer"])


@router.post("/start")
async def start_transfer():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "transfer"})
