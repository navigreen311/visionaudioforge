# VisionAudioForge Python SDK

A pip-installable async Python client for the VisionAudioForge REST API.

## Installation

```bash
pip install visionaudioforge
```

Or install from source:

```bash
pip install -e sdk/python
```

## Quick Start

```python
import asyncio
from visionaudioforge import VAFClient

async def main():
    async with VAFClient(base_url="http://localhost:8000", api_key="your-key") as client:
        # Check health
        status = await client.health()
        print(status)

        # Vision — object detection
        detections = await client.vision.detect("photo.jpg", confidence=0.7)
        for d in detections:
            print(f"{d.label}: {d.confidence:.2f}")

        # Audio — transcription
        transcript = await client.audio.transcribe("recording.wav")
        print(transcript.text)

        # Search — multimodal query
        results = await client.search.query(text="sunset over mountains", k=5)
        for r in results:
            print(f"{r.asset_id} (score={r.score:.3f})")

        # Models — register and promote
        model = await client.models.register("yolov8", "1.0", "csp-darknet")
        await client.models.promote(model.id, "production")

        # Pipelines — create and run
        pipeline = await client.pipeline.create("ingest", {"steps": [...]})
        run = await client.pipeline.run(pipeline.id)

        # Agents — chat with copilot
        answer = await client.agents.chat("Summarize recent alerts")
        print(answer)

asyncio.run(main())
```

## Authentication

The SDK supports two authentication methods:

### API Key

```python
client = VAFClient(api_key="your-api-key")
```

Sends the key via `X-API-Key` header.

### JWT Token (login)

```python
client = VAFClient()
await client.login("user@example.com", "password")
# Token is stored automatically; subsequent requests use Bearer auth.
```

Token-based auth takes precedence over API key when both are set.

## Sub-Clients

| Property            | Module       | Description                       |
|---------------------|--------------|-----------------------------------|
| `client.vision`     | vision.py    | Image analysis, detection, OCR    |
| `client.audio`      | audio.py     | Audio analysis, transcription     |
| `client.models`     | models.py    | Model registry and training       |
| `client.search`     | search.py    | Multimodal search                 |
| `client.pipeline`   | pipeline.py  | Pipeline creation and execution   |
| `client.agents`     | agents.py    | Copilot chat                      |
| `client.datasets`   | datasets.py  | Dataset management                |
| `client.alerts`     | alerts.py    | Alert management                  |
| `client.assets`     | assets.py    | Asset upload and retrieval        |
| `client.transform`  | transform.py | Asset transformations             |

## Async Usage

All methods are async. Use `asyncio.run()` or an existing event loop:

```python
import asyncio
from visionaudioforge import VAFClient

async def analyze():
    async with VAFClient(api_key="key") as client:
        return await client.vision.detect("image.jpg")

results = asyncio.run(analyze())
```

## Error Handling

The SDK raises typed exceptions for HTTP errors:

```python
from visionaudioforge.exceptions import (
    AuthenticationError,  # 401
    PermissionDeniedError,  # 403
    NotFoundError,  # 404
    ValidationError,  # 422
    RateLimitError,  # 429
    ServerError,  # 500
    VAFError,  # base class
)

try:
    await client.models.get_experiment("missing-id")
except NotFoundError:
    print("Experiment not found")
except VAFError as e:
    print(f"API error {e.status_code}: {e.message}")
```
