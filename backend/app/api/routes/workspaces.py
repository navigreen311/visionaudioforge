from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("")
async def list_workspaces():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "workspaces"})


@router.post("")
async def create_workspace():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "workspaces"})
