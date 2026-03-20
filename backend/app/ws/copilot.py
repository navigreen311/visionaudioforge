"""WebSocket endpoint for streaming copilot chat."""

import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from app.services.agents.copilot import CopilotService

logger = logging.getLogger(__name__)

copilot_service = CopilotService()


async def copilot_ws_handler(websocket: WebSocket) -> None:
    """Handle streaming copilot chat over WebSocket.

    Receive: {"message": str, "agent_id": str, "skill_pack": str}
    Send: {"type": "token", "content": str}
         | {"type": "tool_use", "tool": str, "input": dict}
         | {"type": "done"}
         | {"type": "error", "content": str}
    """
    await websocket.accept()
    logger.info("Copilot WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "content": "Invalid JSON payload"}
                )
                continue

            message = data.get("message", "").strip()
            if not message:
                await websocket.send_json(
                    {"type": "error", "content": "Empty message"}
                )
                continue

            agent_id = data.get("agent_id", str(uuid.uuid4()))
            skill_pack = data.get("skill_pack", "general")
            workspace_id = data.get("workspace_id", "default")

            try:
                async for event in copilot_service.chat(
                    message=message,
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    skill_pack=skill_pack,
                ):
                    if event["type"] == "token":
                        await websocket.send_json({
                            "type": "token",
                            "content": event["content"],
                        })
                    elif event["type"] in ("tool_use_start", "tool_result"):
                        await websocket.send_json({
                            "type": "tool_use",
                            "tool": event.get("tool", ""),
                            "input": event.get("input", {}),
                        })
                    elif event["type"] == "done":
                        await websocket.send_json({"type": "done"})

            except Exception as e:
                logger.exception("Error during copilot chat stream")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Stream error: {str(e)}",
                })
                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Copilot WebSocket disconnected")
