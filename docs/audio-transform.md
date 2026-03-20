# Audio Transform Studio

## Overview

The Audio Transform Studio provides a chain-based audio processing pipeline. Users upload audio, configure a sequence of transform operations, and receive the processed result with before/after comparison.

## Architecture

```
Frontend (React)          API (FastAPI)              Service
┌──────────────┐    POST  ┌──────────────────┐    ┌─────────────────────┐
│ Upload +     │ ──────── │ /api/transform/  │ ── │ AudioTransformService│
│ Chain Builder│  file +  │      audio       │    │  .apply_chain()     │
│ + Waveform   │  ops     └──────────────────┘    └─────────────────────┘
└──────────────┘                                     │ denoise
                                                     │ remove_silence
                                                     │ pitch_shift
                                                     │ time_stretch
                                                     │ normalize_loudness
                                                     │ apply_eq
                                                     │ speech_enhance
```

## API

### POST /api/transform/audio

**Content-Type:** multipart/form-data

| Field      | Type       | Description                                       |
|------------|------------|---------------------------------------------------|
| file       | UploadFile | Audio file (WAV, MP3, FLAC, OGG, etc.)           |
| operations | string     | JSON array of transform steps or a preset object  |

**Operations format (chain):**
```json
[
  {"op": "denoise"},
  {"op": "pitch", "params": {"semitones": 2}},
  {"op": "loudness", "params": {"target_lufs": -14}}
]
```

**Operations format (preset):**
```json
{"preset": "podcast"}
```

**Available operations:**

| op        | params                                     | Description                    |
|-----------|--------------------------------------------|--------------------------------|
| denoise   | method (default: spectral_gating)          | Spectral-gating noise removal  |
| silence   | threshold_db (-40), min_silence_ms (500)   | Remove silent segments         |
| pitch     | semitones (0, clamped -12..12)             | Pitch shift via librosa        |
| stretch   | rate (1.0, clamped 0.5..2.0)              | Time stretch via librosa       |
| loudness  | target_lufs (-14.0)                        | RMS-based loudness normalize   |
| eq        | preset (flat/voice/music/podcast)          | Parametric EQ presets          |
| enhance   | (none)                                     | Chain: silence+denoise+loud+eq |

**Response:**
```json
{
  "audio": "<base64-encoded WAV>",
  "format": "wav",
  "original_duration_s": 5.0,
  "output_duration_s": 4.8,
  "operations_applied": ["denoise", "pitch", "loudness"],
  "processing_time_ms": 342.5
}
```

## EQ Presets

- **flat** — No change (passthrough).
- **voice** — High-pass at 100 Hz, boost 300-3000 Hz.
- **music** — Bass boost below 250 Hz, treble boost above 6 kHz.
- **podcast** — High-pass at 80 Hz, presence boost 2-4 kHz, gentle compression.

## Frontend

The Transform page (`/transform`) has two tabs:

1. **Audio Transform** — Upload, waveform display, preset buttons (Podcast Cleanup, Voice Enhancement, Music Master, Custom), chain builder with add/remove/reorder, Apply button, before/after waveforms, dual audio players, download.
2. **Video Transform** — Placeholder for WS-18.

## Running Tests

```bash
cd backend
python -m pytest tests/test_audio_transform.py -v
```

## Environment Variables

No additional environment variables required. Uses standard backend configuration.

## Dependencies

- `librosa` — pitch shift, time stretch
- `scipy` — STFT/ISTFT, butterworth filters
- `soundfile` — audio I/O
- `numpy` — array operations
