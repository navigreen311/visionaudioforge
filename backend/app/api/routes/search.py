from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/query")
async def search_query():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "search"})
