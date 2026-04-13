from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# In-memory stub data
_notifications = [
    {
        "id": "notif_001",
        "type": "alert",
        "title": "Critical alert triggered",
        "description": "Person detected in Zone B",
        "read": False,
        "created_at": "2026-04-13T10:30:00Z",
        "action_url": "/alerts",
    },
    {
        "id": "notif_002",
        "type": "pipeline",
        "title": "Pipeline completed",
        "description": "Camera Detection ran successfully",
        "read": False,
        "created_at": "2026-04-13T09:15:00Z",
        "action_url": "/pipeline",
    },
    {
        "id": "notif_003",
        "type": "model",
        "title": "Model training complete",
        "description": "VisionModel v1.2 ready for review",
        "read": True,
        "created_at": "2026-04-12T14:00:00Z",
        "action_url": "/train",
    },
    {
        "id": "notif_004",
        "type": "asset",
        "title": "New assets uploaded",
        "description": "12 images added to Dataset-A",
        "read": False,
        "created_at": "2026-04-12T11:30:00Z",
        "action_url": "/assets",
    },
    {
        "id": "notif_005",
        "type": "system",
        "title": "System maintenance",
        "description": "Scheduled maintenance tonight",
        "read": True,
        "created_at": "2026-04-11T16:00:00Z",
        "action_url": "/settings",
    },
]


@router.get("")
async def list_notifications(limit: int = Query(50)):
    return _notifications[:limit]


@router.get("/unread-count")
async def unread_count():
    return {"count": sum(1 for n in _notifications if not n["read"])}


@router.patch("/{notif_id}/read")
async def mark_read(notif_id: str):
    for n in _notifications:
        if n["id"] == notif_id:
            n["read"] = True
            return {"success": True}
    return {"success": False}


@router.post("/read-all")
async def read_all():
    for n in _notifications:
        n["read"] = True
    return {"success": True}
