# Capture Engine (M1)

Live capture engine for real-time vision and audio input with WebSocket streaming.

## Architecture

```
Browser (Camera/Screen/Mic)
  │
  │  frames @ 5 FPS (base64 JPEG)
  ▼
WebSocket  /ws/live/stream/{session_id}
  │
  ▼
CaptureWebSocket (backend/app/ws/capture.py)
  ├── decode base64 → numpy via OpenCV
  ├── compute brightness (mean gray)
  ├── detect motion (frame diff > threshold)
  └── return JSON { frame_id, analysis, detections }
  │
  ▼
ConnectionManager (backend/app/ws/manager.py)
  └── channel-based WebSocket routing & broadcast
```

## Backend Components

### WebSocket Route

```
WS /ws/live/stream/{session_id}
```

Accepts a WebSocket connection. Each JSON message must contain `{ "frame": "<base64-jpeg>" }`. Returns analysis results per frame.

### CaptureWebSocket (`backend/app/ws/capture.py`)

Handles a single capture session. Decodes frames, runs lightweight analysis (brightness, motion, resolution), returns structured results.

### ConnectionManager (`backend/app/ws/manager.py`)

Channel-based WebSocket manager:
- `connect(websocket, channel)` — accept and track
- `disconnect(websocket, channel)` — remove from channel
- `broadcast(channel, message)` — send to all in channel
- `get_connection_count(channel?)` — count connections

### CaptureSessionManager (`backend/app/services/capture/manager.py`)

In-memory session lifecycle (swap for Redis in production):
- `create_session(workspace_id, source_type, config?)` — returns session info
- `end_session(session_id)` — returns duration and frame count
- `list_active_sessions(workspace_id)` — active sessions for workspace

## Frontend Components

| Component | Path | Purpose |
|-----------|------|---------|
| CapturePage | `frontend/src/app/(dashboard)/capture/page.tsx` | Full capture UI |
| LiveFeedPanel | `frontend/src/components/capture/LiveFeedPanel.tsx` | Video + AI overlay |
| AudioMeter | `frontend/src/components/capture/AudioMeter.tsx` | Real-time audio levels |
| SourceSwitcher | `frontend/src/components/capture/SourceSwitcher.tsx` | Camera/Screen/Mic tabs |
| CaptureControls | `frontend/src/components/capture/CaptureControls.tsx` | Start/Stop/Snapshot |

## Running

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev
```

Open `http://localhost:3000/capture`, click Start to begin streaming.

## Tests

```bash
cd backend && python -m pytest tests/test_capture.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | WebSocket server URL |
