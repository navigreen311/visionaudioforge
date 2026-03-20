# Audio Augmentation Pipeline

## Overview

The audio augmentation module provides a configurable pipeline for generating diverse training data from existing audio samples. It supports waveform-level transformations (noise injection, time stretching, pitch shifting, time shifting) and spectrogram-level SpecAugment masking (frequency and time masking).

## Architecture

```
AudioAugmenter (service)
├── add_noise()          — white / pink / brown noise at target SNR
├── time_stretch()       — librosa time-stretch without pitch change
├── pitch_shift()        — semitone-based pitch shifting
├── time_shift()         — temporal offset with zero-padding
├── frequency_mask()     — SpecAugment frequency masking
├── time_mask()          — SpecAugment time masking
├── apply_pipeline()     — probabilistic sequential pipeline
└── augment_batch()      — batch processing with multiple versions

augmentation_presets.py
├── speech_robust        — moderate noise + mild stretch/pitch
├── music_robust         — moderate noise + wider stretch/pitch range
├── environmental        — heavy noise + time shifts
├── light                — subtle augmentations
└── heavy                — aggressive augmentations
```

## API Endpoint

### POST `/api/audio/augment`

Augment an uploaded audio file using a preset or custom pipeline.

**Request** (multipart form):

| Field    | Type           | Description                                              |
|----------|----------------|----------------------------------------------------------|
| `file`   | `UploadFile`   | Audio file (WAV, MP3, FLAC, etc.)                        |
| `config` | `string`       | Preset name (e.g. `"light"`) or JSON array of steps      |

**Custom config example:**

```json
[
  {"type": "noise", "probability": 0.8, "params": {"noise_type": "white", "snr_db": 15}},
  {"type": "stretch", "probability": 0.5, "params": {"rate": 1.1}},
  {"type": "pitch", "probability": 0.3, "params": {"n_steps": 2}}
]
```

**Response:**

```json
{
  "augmented_audio": "<base64-encoded WAV>",
  "applied_augmentations": [{"type": "noise", "params": {"snr_db": 15}}],
  "original_duration_s": 3.5,
  "augmented_duration_s": 3.5,
  "processing_time_ms": 142.3
}
```

## Augmentation Types

| Type      | Key Params                     | Notes                                        |
|-----------|--------------------------------|----------------------------------------------|
| `noise`   | `noise_type`, `snr_db`         | white, pink (1/f), brown (random walk)       |
| `stretch` | `rate`                         | Clamped to [0.5, 2.0]; >1 = faster           |
| `pitch`   | `n_steps`                      | Semitones, clamped to [-12, 12]              |
| `shift`   | `shift_ms`                     | Positive = delay, negative = advance         |

## Presets

| Preset          | Use Case                          |
|-----------------|-----------------------------------|
| `speech_robust` | ASR / speech classification       |
| `music_robust`  | Music genre / instrument tasks    |
| `environmental` | Environmental sound detection     |
| `light`         | Subtle augmentation               |
| `heavy`         | Maximum diversity                 |

## Running Tests

```bash
cd backend
pytest tests/test_audio_augmentation.py -v
```

## Environment Variables

No additional environment variables required. The module uses `librosa`, `numpy`, and `soundfile` which must be installed (see `requirements.txt`).
