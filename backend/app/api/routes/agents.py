from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/chat")
async def agent_chat():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "agents"})
