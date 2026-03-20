from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "auth"})


@router.post("/register")
async def register():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "auth"})
