"""Audio processing services: spectral analysis, I/O, visualization, STT, VAD, separation, classification, diarization, keyword spotting, call intelligence."""

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
from app.services.audio.diarization import SpeakerDiarizer
from app.services.audio.keyword_spotter import KeywordSpotter
from app.services.audio.call_intelligence import CallIntelligence

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
    "SpeakerDiarizer",
    "KeywordSpotter",
    "CallIntelligence",
]
