# Audio Spectral Analysis

## Overview

End-to-end audio spectral analysis service providing STFT, Mel spectrogram, MFCC extraction, power spectrogram computation, waveform statistics, and automatic visualization generation.

## Architecture

```
POST /api/audio/analyze
  ├── Audio I/O (io.py)          — load, validate, encode
  ├── SpectralAnalyzer (spectral.py)
  │     ├── compute_stft()
  │     ├── compute_mel_spectrogram()
  │     ├── compute_mfcc()
  │     ├── compute_power_spectrogram()
  │     ├── compute_waveform_stats()
  │     └── extract_all_features()
  └── Visualization (visualization.py)
        ├── plot_spectrogram()
        ├── plot_mel_spectrogram()
        ├── plot_mfcc()
        └── plot_waveform()
```

## API Endpoint

### `POST /api/audio/analyze`

**Form fields:**

| Field        | Type       | Description                                        |
|-------------|------------|----------------------------------------------------|
| `file`      | UploadFile | Audio file (WAV, FLAC, OGG, etc.)                  |
| `operations`| string     | JSON array: `["stft","mel","mfcc","waveform","power","all"]` |

**Response (200):**

```json
{
  "features": {
    "stft": { "shape": [1025, 44], "visualization": "<base64 PNG>" },
    "mel":  { "shape": [128, 44],  "visualization": "<base64 PNG>" },
    "mfcc": { "shape": [13, 44],   "visualization": "<base64 PNG>", "coefficients": [[...]] },
    "waveform": { "visualization": "<base64 PNG>", "stats": { "duration_s": 1.0, "rms": 0.707, ... } }
  },
  "audio_info": { "duration_s": 1.0, "sample_rate": 22050, "samples": 22050 },
  "processing_time_ms": 142.5
}
```

**Constraints:**

- Max file size: 50 MB
- Max duration: 300 seconds

## Key Parameters

| Parameter    | Default | Description                          |
|-------------|---------|--------------------------------------|
| `n_fft`     | 2048    | FFT window size                      |
| `hop_length`| 512     | Hop between frames                   |
| `n_mels`    | 128     | Number of Mel filter banks           |
| `n_mfcc`    | 13      | Number of MFCC coefficients          |
| `window`    | hann    | Window function for STFT             |

## Running Tests

```bash
cd backend
pytest tests/test_audio_spectral.py -v
```

## Dependencies

- `librosa==0.10.1` — spectral analysis and feature extraction
- `soundfile==0.12.1` — audio I/O
- `matplotlib` — visualization (Agg backend for headless rendering)
- `numpy==1.26.4` — numerical operations
