# @visionaudioforge/sdk

JavaScript/TypeScript SDK for the VisionAudioForge API. Zero dependencies -- uses native `fetch` (Node.js 18+ and all modern browsers).

## Installation

```bash
npm install @visionaudioforge/sdk
```

## Quick Start

```typescript
import { VAFClient } from '@visionaudioforge/sdk';

const client = new VAFClient({ baseUrl: 'http://localhost:8000' });

// Login with credentials
await client.login('user', 'password');

// Or use an API key
const client2 = new VAFClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key',
});

// Check service health (no auth required)
const health = await client.health();
```

## Sub-Clients

The SDK is organized into sub-clients, each covering a domain of the API:

| Property          | Class             | Domain                        |
|-------------------|-------------------|-------------------------------|
| `client.vision`   | `VisionClient`    | Image analysis, detection, OCR |
| `client.audio`    | `AudioClient`     | Spectral analysis, augmentation |
| `client.models`   | `ModelClient`     | Model registry, training       |
| `client.search`   | `SearchClient`    | Cross-modal search (CLIP)      |
| `client.pipeline` | `PipelineClient`  | Pipeline builder               |
| `client.agents`   | `AgentClient`     | AI copilot chat                |
| `client.datasets` | `DatasetClient`   | Dataset management             |
| `client.alerts`   | `AlertClient`     | Alerting rules                 |
| `client.assets`   | `AssetClient`     | File/asset storage             |
| `client.transform`| `TransformClient` | Audio & video transforms       |

## Examples

### Vision -- Object Detection

```typescript
const imageBlob = await fetch('/path/to/image.jpg').then(r => r.blob());
const detections = await client.vision.detect(imageBlob);
console.log(detections.objects); // [{ label: 'car', confidence: 0.95, bbox: [...] }]
```

### Vision -- OCR

```typescript
const ocrResult = await client.vision.ocr(imageBlob);
console.log(ocrResult.text);
```

### Audio -- Spectral Analysis

```typescript
const audioBlob = new Blob([audioBuffer], { type: 'audio/wav' });
const analysis = await client.audio.analyze(audioBlob);
console.log(analysis.duration, analysis.sample_rate);
```

### Models -- Register and Promote

```typescript
const model = await client.models.register({
  name: 'yolo-v8-custom',
  version: '1.0.0',
  framework: 'pytorch',
  metrics: { mAP: 0.89 },
});

await client.models.promote(model.id, 'production');
```

### Search -- Cross-Modal Query

```typescript
const results = await client.search.query({
  query: 'red car on highway',
  modality: 'text',
  top_k: 5,
});
```

### Pipeline -- Create and Run

```typescript
const pipeline = await client.pipeline.create({
  name: 'detect-and-crop',
  nodes: [
    { id: 'detect', type: 'vision.detect', config: {} },
    { id: 'crop', type: 'transform.crop', config: {}, depends_on: ['detect'] },
  ],
});

const run = await client.pipeline.run(pipeline.id);
```

### Agents -- Chat

```typescript
const response = await client.agents.chat({
  message: 'Summarize the latest experiment results',
});
console.log(response.response);
```

### Datasets -- Create and Split

```typescript
const dataset = await client.datasets.create({
  name: 'training-v2',
  type: 'image_classification',
});

await client.datasets.split(dataset.id, {
  train_ratio: 0.8,
  val_ratio: 0.1,
  test_ratio: 0.1,
});
```

### Alerts -- Create Rule

```typescript
await client.alerts.createRule({
  name: 'high-latency',
  metric: 'inference_latency_ms',
  condition: 'gt',
  threshold: 500,
});
```

### Assets -- Upload and Download

```typescript
const uploaded = await client.assets.upload(fileBlob);
console.log(uploaded.url);

const assets = await client.assets.list();
```

### Transform -- Audio and Video

```typescript
// Denoise audio
const denoised = await client.transform.audioDenoise(audioBlob);

// Super-resolution video
const upscaled = await client.transform.videoSuperResolution(videoBlob, {
  scale: 4,
});
```

## Error Handling

The SDK throws typed errors that you can catch and inspect:

```typescript
import { AuthError, NotFoundError, ValidationError, ServerError, VAFError } from '@visionaudioforge/sdk';

try {
  await client.models.get('nonexistent-id');
} catch (err) {
  if (err instanceof NotFoundError) {
    console.log('Model not found');
  } else if (err instanceof AuthError) {
    console.log('Authentication failed -- re-login');
  } else if (err instanceof ValidationError) {
    console.log('Bad request:', err.detail);
  } else if (err instanceof ServerError) {
    console.log('Server error, try again later');
  }
}
```

All errors extend `VAFError` which includes `statusCode` and `detail` properties.

## Browser Usage

The SDK works out of the box in modern browsers:

```html
<script type="module">
  import { VAFClient } from '@visionaudioforge/sdk';

  const client = new VAFClient({ baseUrl: 'https://api.example.com' });
  await client.login('user', 'pass');

  const fileInput = document.querySelector('input[type="file"]');
  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const result = await client.vision.analyze(file);
    console.log(result);
  });
</script>
```

## Node.js Usage

Requires Node.js 18+ (native `fetch`):

```typescript
import { VAFClient } from '@visionaudioforge/sdk';
import { readFileSync } from 'fs';

const client = new VAFClient({
  baseUrl: 'http://localhost:8000',
  apiKey: process.env.VAF_API_KEY,
});

const health = await client.health();
console.log(health.status);
```

## Request Options

All methods accept an optional `RequestOptions` object as the last parameter:

```typescript
const controller = new AbortController();

// Cancel request after 5 seconds
setTimeout(() => controller.abort(), 5000);

const result = await client.vision.detect(imageBlob, {
  signal: controller.signal,
  headers: { 'X-Request-Id': 'custom-id' },
});
```

## TypeScript

All response types are exported and can be imported directly:

```typescript
import type { DetectionResult, ModelInfo, SearchResult } from '@visionaudioforge/sdk';
```
