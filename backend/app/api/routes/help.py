from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/help", tags=["help"])


@router.get("/search")
async def search_help(q: str = Query("")):
    articles = [
        {"id": "1", "title": "Getting Started Guide", "summary": "Learn the basics of VisionAudioForge"},
        {"id": "2", "title": "Pipeline Builder Guide", "summary": "Create automated AI workflows"},
        {"id": "3", "title": "Audio Analysis Tutorial", "summary": "Analyze audio with spectral tools"},
    ]
    if q:
        articles = [
            a for a in articles
            if q.lower() in a["title"].lower() or q.lower() in a["summary"].lower()
        ]
    return {"articles": articles}
