from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/profile", tags=["profile"])

_profile = {
    "id": "user_001",
    "email": "ivan@visionaudioforge.com",
    "display_name": "Ivan",
    "bio": "",
    "role": "admin",
    "avatar_url": None,
    "member_since": "2026-04-13T00:00:00Z",
    "activity": {
        "tasks_completed": 12,
        "assets_uploaded": 34,
        "pipelines_created": 5,
        "reviews_completed": 8,
    },
}


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None


@router.get("/api/profile")
async def get_profile():
    return _profile


@router.patch("/api/profile")
async def update_profile(body: ProfileUpdate):
    if body.display_name is not None:
        _profile["display_name"] = body.display_name
    if body.bio is not None:
        _profile["bio"] = body.bio
    return _profile


@router.post("/api/profile/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    _profile["avatar_url"] = f"/uploads/{file.filename}"
    return {"avatar_url": _profile["avatar_url"]}
