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


def plot_waveform(
    audio: np.ndarray,
    sr: int,
    title: str = "Waveform",
) -> str:
    """Plot the raw waveform and return a base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 4))
    librosa.display.waveshow(audio, sr=sr, ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    return _fig_to_base64(fig)
