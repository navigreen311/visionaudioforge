"""Audio processing services: spectral analysis, I/O, visualization, STT, VAD, separation, classification."""

from app.services.audio.spectral import SpectralAnalyzer
from app.services.audio.io import load_audio, save_audio, audio_to_base64, validate_audio
from app.services.audio.visualization import (
    plot_spectrogram,
    plot_mel_spectrogram,
    plot_mfcc,
    plot_waveform,
)
from app.services.audio.stt import SpeechToTextService
from app.services.audio.vad import VoiceActivityDetector
from app.services.audio.separation import SourceSeparator
from app.services.audio.classification import AudioClassifier
from app.services.audio.voice_biometrics import VoiceBiometrics
from app.services.audio.fingerprinting import AudioFingerprinter
from app.services.audio.av_sync import AVSyncDetector
from app.services.audio.audio_embeddings import AudioEmbeddingService
from app.services.audio.translation import AudioTranslator

__all__ = [
    "SpectralAnalyzer",
    "load_audio",
    "save_audio",
    "audio_to_base64",
    "validate_audio",
    "plot_spectrogram",
    "plot_mel_spectrogram",
    "plot_mfcc",
    "plot_waveform",
    "SpeechToTextService",
    "VoiceActivityDetector",
    "SourceSeparator",
    "AudioClassifier",
    "VoiceBiometrics",
    "AudioFingerprinter",
    "AVSyncDetector",
    "AudioEmbeddingService",
    "AudioTranslator",
]
