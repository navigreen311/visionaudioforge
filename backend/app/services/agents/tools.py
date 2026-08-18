"""Tool definitions and execution for the copilot agent.

Wired to real services with graceful fallbacks when services are unavailable.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

# A 2s budget is not enough on a dual-stack host: "localhost" resolves to ::1
# first, and when the server listens on IPv4 only the whole budget is spent on
# the IPv6 attempt before IPv4 is tried. The check then reports a Redis that is
# up as down — a health check that cries wolf is worse than none.
REDIS_CONNECT_TIMEOUT_S = 5

logger = logging.getLogger(__name__)

COPILOT_TOOLS: list[dict] = [
    {
        "name": "search_media",
        "description": "Search the media library using text, image, or audio queries",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "modality": {
                    "type": "string",
                    "enum": ["text", "image", "audio"],
                    "description": "Type of search modality",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "analyze_image",
        "description": "Analyze an image for objects, text, and visual properties",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path or ID of the image to analyze",
                },
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "analyze_audio",
        "description": "Analyze audio for spectral features, duration, and characteristics",
        "input_schema": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path or ID of the audio file to analyze",
                },
            },
            "required": ["audio_path"],
        },
    },
    {
        "name": "create_alert",
        "description": "Create a new alert in the system",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "error", "critical"],
                    "description": "Alert severity level",
                },
                "message": {
                    "type": "string",
                    "description": "Alert message content",
                },
                "details": {
                    "type": "string",
                    "description": "Additional details or context",
                },
            },
            "required": ["severity", "message"],
        },
    },
    {
        "name": "query_events",
        "description": "Query recent events from the event log",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type",
                },
                "hours_back": {
                    "type": "integer",
                    "description": "How many hours back to query (default 24)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default 20)",
                },
            },
        },
    },
    {
        "name": "get_system_status",
        "description": "Get platform health and operational statistics",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "query_knowledge_graph",
        "description": (
            "Query the knowledge graph for entity relationships, event connections, "
            "and spatial-temporal patterns. Use this to find how entities are related, "
            "trace paths between people/objects/locations, and discover patterns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural language query about entities, relationships, or events. "
                        "Examples: 'who was near the warehouse', 'how is John connected to "
                        "the vehicle', 'find all people near Main Street'"
                    ),
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Real service executors
# ---------------------------------------------------------------------------


async def _search_media_real(query: str, modality: str) -> dict:
    """Search using CrossModalSearchService."""
    try:
        from app.services.search.embeddings import EmbeddingService
        from app.services.search.faiss_index import FAISSIndexService
        from app.services.search.search_service import CrossModalSearchService

        embedding_svc = EmbeddingService()
        index_svc = FAISSIndexService(dimension=embedding_svc.dimension)
        search_svc = CrossModalSearchService(embedding_svc, index_svc)

        results = await search_svc.search_by_text(query, k=10, modality_filter=modality if modality != "text" else None)
        return {
            "results": results,
            "total_count": len(results),
            "query": query,
            "modality": modality,
        }
    except Exception as exc:
        logger.warning("search_media service unavailable: %s", exc)
        return {
            "results": [],
            "total_count": 0,
            "query": query,
            "modality": modality,
            "note": f"Search service temporarily unavailable: {exc}",
        }


async def _analyze_image_real(image_path: str) -> dict:
    """Analyze image using ImagePreprocessor and ObjectDetector."""
    try:
        import cv2
        import numpy as np

        from app.services.vision.detection import ObjectDetector
        from app.services.vision.preprocessing import ImagePreprocessor

        # Attempt to load from local path first, then try MinIO
        image = None
        try:
            image = cv2.imread(image_path)
            if image is not None:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception:
            pass

        if image is None:
            # Try loading from MinIO
            try:
                from minio import Minio

                from app.config import settings

                client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=False,
                )
                response = client.get_object(settings.MINIO_BUCKET, image_path)
                data = response.read()
                response.close()
                response.release_conn()
                arr = np.frombuffer(data, np.uint8)
                image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if image is not None:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            except Exception as minio_err:
                logger.warning("Could not load image from MinIO: %s", minio_err)

        if image is None:
            return {
                "image_path": image_path,
                "error": "Could not load image from local path or MinIO.",
            }

        # Run detection
        detector = ObjectDetector()
        detections = detector.detect(image, confidence=0.5)

        # Calculate image stats
        preprocessor = ImagePreprocessor()
        height, width = image.shape[:2]
        channels = image.shape[2] if image.ndim == 3 else 1

        # Dominant colors via simple k-means approximation
        dominant_colors = []
        try:
            pixels = image.reshape(-1, 3).astype(np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, _, centers = cv2.kmeans(pixels, 3, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
            for c in centers:
                dominant_colors.append("#{:02X}{:02X}{:02X}".format(int(c[0]), int(c[1]), int(c[2])))
        except Exception:
            pass

        return {
            "image_path": image_path,
            "objects_detected": [
                {
                    "label": d["class_name"],
                    "confidence": round(d["confidence"], 3),
                    "bbox": [round(v, 1) for v in d["bbox"]],
                }
                for d in detections
            ],
            "properties": {
                "width": width,
                "height": height,
                "channels": channels,
                "mean_intensity": round(float(image.mean()), 2),
                "std_intensity": round(float(image.std()), 2),
                "dominant_colors": dominant_colors,
            },
        }
    except ImportError as exc:
        logger.warning("Image analysis dependencies unavailable: %s", exc)
        return {
            "image_path": image_path,
            "error": f"Image analysis dependencies not installed: {exc}",
        }
    except Exception as exc:
        logger.warning("Image analysis failed: %s", exc)
        return {
            "image_path": image_path,
            "error": f"Image analysis failed: {exc}",
        }


async def _analyze_audio_real(audio_path: str) -> dict:
    """Analyze audio using SpectralAnalyzer."""
    try:
        import numpy as np

        from app.services.audio.spectral import SpectralAnalyzer

        # Load audio
        audio = None
        sr = None
        try:
            import librosa

            audio, sr = librosa.load(audio_path, sr=None)
        except Exception:
            pass

        if audio is None:
            # Try loading from MinIO
            try:
                import io

                import soundfile as sf
                from minio import Minio

                from app.config import settings

                client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=False,
                )
                response = client.get_object(settings.MINIO_BUCKET, audio_path)
                data = response.read()
                response.close()
                response.release_conn()
                audio, sr = sf.read(io.BytesIO(data))
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                audio = audio.astype(np.float32)
            except Exception as minio_err:
                logger.warning("Could not load audio from MinIO: %s", minio_err)

        if audio is None or sr is None:
            return {
                "audio_path": audio_path,
                "error": "Could not load audio from local path or MinIO.",
            }

        analyzer = SpectralAnalyzer()

        # Waveform stats
        waveform_stats = analyzer.compute_waveform_stats(audio, sr)

        # MFCC
        mfcc_data = analyzer.compute_mfcc(audio, sr)
        mfcc_shape = list(mfcc_data["mfcc"].shape)

        return {
            "audio_path": audio_path,
            "duration_seconds": round(waveform_stats["duration_s"], 2),
            "sample_rate": waveform_stats["sample_rate"],
            "rms": round(waveform_stats["rms"], 4),
            "peak_amplitude": round(waveform_stats["peak_amplitude"], 4),
            "zero_crossing_rate": round(waveform_stats["zero_crossing_rate"], 4),
            "is_silent": waveform_stats["is_silent"],
            "mfcc_shape": mfcc_shape,
        }
    except ImportError as exc:
        logger.warning("Audio analysis dependencies unavailable: %s", exc)
        return {
            "audio_path": audio_path,
            "error": f"Audio analysis dependencies not installed: {exc}",
        }
    except Exception as exc:
        logger.warning("Audio analysis failed: %s", exc)
        return {
            "audio_path": audio_path,
            "error": f"Audio analysis failed: {exc}",
        }


async def _create_alert_real(severity: str, message: str, details: str) -> dict:
    """Create a copilot_alert Event record."""
    now = datetime.now(timezone.utc)
    try:
        from app.database import async_session_factory
        from app.models.event import Event

        async with async_session_factory() as session:
            # Use a sentinel workspace ID for copilot-generated alerts
            workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
            event = Event(
                type="copilot_alert",
                payload={
                    "severity": severity,
                    "message": message,
                    "details": details,
                },
                source="copilot",
                workspace_id=workspace_id,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return {
                "alert_id": str(event.id),
                "severity": severity,
                "message": message,
                "details": details,
                "created_at": event.timestamp.isoformat() if event.timestamp else now.isoformat(),
                "status": "active",
            }
    except Exception as exc:
        logger.warning("Could not create alert in DB: %s", exc)
        return {
            "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
            "severity": severity,
            "message": message,
            "details": details,
            "created_at": now.isoformat(),
            "status": "active",
            "note": f"Alert created in-memory only (DB unavailable: {exc})",
        }


async def _query_events_real(event_type: str | None, hours_back: int, limit: int) -> dict:
    """Query Event table from DB."""
    try:
        from sqlalchemy import select

        from app.database import async_session_factory
        from app.models.event import Event

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        async with async_session_factory() as session:
            stmt = select(Event).where(Event.timestamp >= cutoff)

            if event_type and event_type != "all":
                stmt = stmt.where(Event.type == event_type)

            stmt = stmt.order_by(Event.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            events = result.scalars().all()

            return {
                "events": [
                    {
                        "id": str(e.id),
                        "event_type": e.type,
                        "source": e.source,
                        "payload": e.payload,
                        "timestamp": e.timestamp.isoformat() if e.timestamp else "",
                    }
                    for e in events
                ],
                "total_count": len(events),
                "hours_back": hours_back,
                "limit": limit,
            }
    except Exception as exc:
        logger.warning("Could not query events from DB: %s", exc)
        return {
            "events": [],
            "total_count": 0,
            "hours_back": hours_back,
            "limit": limit,
            "note": f"Event query unavailable: {exc}",
        }


async def _get_system_status_real() -> dict:
    """Check real system health (DB, Redis)."""
    now = datetime.now(timezone.utc).isoformat()
    services: dict[str, str] = {}

    # Check database
    try:
        from sqlalchemy import text

        from app.database import async_session_factory

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        services["database"] = "up"
    except Exception:
        services["database"] = "down"

    # Check Redis
    try:
        import redis.asyncio as aioredis

        from app.config import settings

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=REDIS_CONNECT_TIMEOUT_S)
        await r.ping()
        await r.aclose()
        services["redis"] = "up"
    except Exception:
        services["redis"] = "down"

    # Check MinIO
    try:
        from minio import Minio

        from app.config import settings

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        client.list_buckets()
        services["minio"] = "up"
    except Exception:
        services["minio"] = "unknown"

    # Get stats from DB if available
    stats: dict = {}
    try:
        from sqlalchemy import func, select

        from app.database import async_session_factory
        from app.models.alert import Alert, AlertStatus
        from app.models.asset import Asset

        async with async_session_factory() as session:
            total_assets = (await session.execute(select(func.count()).select_from(Asset))).scalar() or 0
            pending_alerts = (
                await session.execute(
                    select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.new)
                )
            ).scalar() or 0
            stats = {
                "total_assets": total_assets,
                "pending_alerts": pending_alerts,
            }
    except Exception:
        stats = {"note": "Stats unavailable (DB issue)"}

    # Overall status
    if services.get("database") == "down":
        overall = "unhealthy"
    elif services.get("redis") == "down":
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "services": services,
        "stats": stats,
        "checked_at": now,
    }


async def _query_knowledge_graph_real(query: str) -> dict:
    """Query the knowledge graph using GraphRAGService."""
    try:
        from app.database import async_session_factory
        from app.services.knowledge_graph.graph_rag import GraphRAGService

        service = GraphRAGService()
        workspace_id = "00000000-0000-0000-0000-000000000001"

        async with async_session_factory() as session:
            result = await service.query_graph_nl(session, query, workspace_id)
            return result
    except Exception as exc:
        logger.warning("Knowledge graph query failed: %s", exc)
        return {
            "answer": f"Knowledge graph query failed: {exc}",
            "evidence_nodes": [],
            "confidence": 0.0,
        }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a JSON string.

    Wired to real services with graceful fallbacks.
    """
    if tool_name == "search_media":
        query = tool_input.get("query", "")
        modality = tool_input.get("modality", "text")
        result = await _search_media_real(query, modality)
        return json.dumps(result, default=str)

    elif tool_name == "analyze_image":
        image_path = tool_input.get("image_path", "unknown")
        result = await _analyze_image_real(image_path)
        return json.dumps(result, default=str)

    elif tool_name == "analyze_audio":
        audio_path = tool_input.get("audio_path", "unknown")
        result = await _analyze_audio_real(audio_path)
        return json.dumps(result, default=str)

    elif tool_name == "create_alert":
        severity = tool_input.get("severity", "info")
        message = tool_input.get("message", "")
        details = tool_input.get("details", "")
        result = await _create_alert_real(severity, message, details)
        return json.dumps(result, default=str)

    elif tool_name == "query_events":
        event_type = tool_input.get("event_type")
        hours_back = tool_input.get("hours_back", 24)
        limit = tool_input.get("limit", 20)
        result = await _query_events_real(event_type, hours_back, limit)
        return json.dumps(result, default=str)

    elif tool_name == "get_system_status":
        result = await _get_system_status_real()
        return json.dumps(result, default=str)

    elif tool_name == "query_knowledge_graph":
        query = tool_input.get("query", "")
        result = await _query_knowledge_graph_real(query)
        return json.dumps(result, default=str)

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
