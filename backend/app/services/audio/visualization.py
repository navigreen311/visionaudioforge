"""Visualization helpers: generate base64-encoded PNG plots for audio features."""

from __future__ import annotations

import base64
import io

import librosa.display
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # Non-GUI backend


def _fig_to_base64(fig: plt.Figure) -> str:
    """Render a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------

def plot_spectrogram(
    magnitude: np.ndarray,
    sr: int,
    hop_length: int = 512,
    title: str = "Spectrogram",
) -> str:
    """Plot a magnitude spectrogram and return a base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 4))
    mag_db = librosa.amplitude_to_db(magnitude, ref=np.max)
    img = librosa.display.specshow(
        mag_db, sr=sr, hop_length=hop_length, x_axis="time", y_axis="hz", ax=ax
    )
    ax.set_title(title)
    fig.colorbar(img, ax=ax, format="%+2.0f dB")
    return _fig_to_base64(fig)


def plot_mel_spectrogram(
    mel_spec_db: np.ndarray,
    sr: int,
    hop_length: int = 512,
    title: str = "Mel Spectrogram",
) -> str:
    """Plot a Mel spectrogram (already in dB) and return a base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 4))
    img = librosa.display.specshow(
        mel_spec_db, sr=sr, hop_length=hop_length, x_axis="time", y_axis="mel", ax=ax
    )
    ax.set_title(title)
    fig.colorbar(img, ax=ax, format="%+2.0f dB")
    return _fig_to_base64(fig)


def plot_mfcc(
    mfcc: np.ndarray,
    sr: int,
    hop_length: int = 512,
    title: str = "MFCC",
) -> str:
    """Plot MFCC coefficients and return a base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 4))
    img = librosa.display.specshow(
        mfcc, sr=sr, hop_length=hop_length, x_axis="time", ax=ax
    )
    ax.set_title(title)
    fig.colorbar(img, ax=ax)
    return _fig_to_base64(fig)


#: Above this many samples the waveform is drawn as a min/max envelope rather
#: than sample-by-sample. A plot is at most a couple of thousand pixels wide,
#: so drawing every sample of a long recording costs time and shows nothing
#: extra.
_WAVEFORM_ENVELOPE_THRESHOLD = 4000


def plot_waveform(
    audio: np.ndarray,
    sr: int,
    title: str = "Waveform",
) -> str:
    """Plot the raw waveform and return a base64 PNG.

    Drawn with matplotlib directly rather than `librosa.display.waveshow`.
    waveshow reaches for `axes._get_lines.prop_cycler`, a matplotlib internal
    removed in 3.8 — and requirements.txt pins librosa 0.10.1 against
    matplotlib 3.8.3, so the pinned pair raised AttributeError and every
    waveform plot (and the /audio/analyze responses that include one) failed.
    Plotting here keeps this working on either side of that change.
    """
    fig, ax = plt.subplots(figsize=(10, 4))

    audio = np.asarray(audio, dtype=float)
    if audio.ndim > 1:  # mixdown, as waveshow does
        audio = audio.mean(axis=0)

    duration = len(audio) / sr if sr else 0.0

    if len(audio) > _WAVEFORM_ENVELOPE_THRESHOLD:
        # Min/max envelope: keep both extremes of each bucket so transients
        # survive, which plotting every Nth sample would drop.
        buckets = 2000
        size = len(audio) // buckets
        trimmed = audio[: size * buckets].reshape(buckets, size)
        times = np.linspace(0, duration, buckets)
        ax.fill_between(times, trimmed.min(axis=1), trimmed.max(axis=1), linewidth=0)
    else:
        ax.plot(np.linspace(0, duration, len(audio)), audio, linewidth=0.8)

    ax.set_xlim(0, duration if duration else 1)
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    return _fig_to_base64(fig)
