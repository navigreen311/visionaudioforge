from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("/rules")
async def create_alert_rule():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "alerts"})


@router.get("")
async def list_alerts():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "alerts"})
