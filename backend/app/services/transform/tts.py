"""Text-to-Speech service with placeholder tone-based synthesis.

V1 generates simple tone-based audio shaped by voice presets.
Real TTS requires gTTS, Coqui TTS, or ElevenLabs API.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import numpy as np

# Voice presets: frequency (Hz) for tone generation
_VOICE_PRESETS: dict[str, dict] = {
    "default": {"id": "default", "name": "Default", "language": "en", "gender": "neutral", "freq": 200},
    "male": {"id": "male", "name": "Male", "language": "en", "gender": "male", "freq": 120},
    "female": {"id": "female", "name": "Female", "language": "en", "gender": "female", "freq": 300},
    "narrator": {"id": "narrator", "name": "Narrator", "language": "en", "gender": "neutral", "freq": 180},
    "child": {"id": "child", "name": "Child", "language": "en", "gender": "neutral", "freq": 400},
}

_SAMPLE_RATE = 22050
_CHARS_PER_SECOND = 4.0


class TTSService:
    """Tone-based placeholder TTS service."""

    def available_voices(self) -> list[dict]:
        """Return list of available voice presets."""
        return [
            {"id": v["id"], "name": v["name"], "language": v["language"], "gender": v["gender"]}
            for v in _VOICE_PRESETS.values()
        ]

    def synthesize(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
    ) -> tuple[np.ndarray, int]:
        """Synthesize speech-like audio from text.

        Returns (audio_array, sample_rate).
        Note: This is a placeholder. Real TTS requires gTTS, Coqui TTS,
        or ElevenLabs API.
        """
        preset = _VOICE_PRESETS.get(voice, _VOICE_PRESETS["default"])
        freq = preset["freq"]

        duration_s = max(len(text) / _CHARS_PER_SECOND / speed, 0.1)
        n_samples = int(duration_s * _SAMPLE_RATE)
        t = np.linspace(0, duration_s, n_samples, endpoint=False)

        # Base tone
        audio = np.sin(2 * np.pi * freq * t)

        # Amplitude modulation from text length patterns — makes it speech-like
        # Create an envelope that varies with word boundaries
        words = text.split() if text.strip() else [""]
        word_durations = []
        total_chars = max(sum(len(w) for w in words), 1)
        for w in words:
            word_durations.append(len(w) / total_chars * duration_s)

        envelope = np.ones(n_samples)
        idx = 0
        for wd in word_durations:
            word_samples = int(wd * _SAMPLE_RATE)
            if word_samples <= 0:
                continue
            end_idx = min(idx + word_samples, n_samples)
            seg_len = end_idx - idx
            if seg_len > 0:
                # Attack-sustain-release for each word
                attack = min(int(seg_len * 0.1), seg_len)
                release = min(int(seg_len * 0.2), seg_len - attack)
                sustain = seg_len - attack - release
                word_env = np.concatenate([
                    np.linspace(0.3, 1.0, attack),
                    np.ones(sustain),
                    np.linspace(1.0, 0.2, release),
                ])
                envelope[idx:end_idx] = word_env[:seg_len]
            idx = end_idx
            # Small gap between words
            gap_samples = int(0.05 * _SAMPLE_RATE)
            gap_end = min(idx + gap_samples, n_samples)
            envelope[idx:gap_end] = 0.1
            idx = gap_end

        # Add slight vibrato for naturalness
        vibrato = 1.0 + 0.05 * np.sin(2 * np.pi * 5 * t)
        audio = audio * envelope * vibrato * 0.5

        return audio.astype(np.float32), _SAMPLE_RATE

    def synthesize_ssml(
        self,
        ssml: str,
        voice: str = "default",
    ) -> tuple[np.ndarray, int]:
        """Synthesize from SSML markup with basic tag support.

        Supported tags: <break time="500ms"/>, <emphasis level="strong">.
        """
        # Parse SSML — wrap in root if needed
        if not ssml.strip().startswith("<speak"):
            ssml = f"<speak>{ssml}</speak>"

        try:
            root = ET.fromstring(ssml)
        except ET.ParseError:
            # Fallback: strip tags and synthesize plain text
            plain = re.sub(r"<[^>]+>", " ", ssml)
            return self.synthesize(plain, voice=voice)

        segments: list[np.ndarray] = []

        def _process_element(elem: ET.Element) -> None:
            # Text before children
            if elem.text:
                audio, _ = self.synthesize(elem.text.strip(), voice=voice)
                segments.append(audio)

            for child in elem:
                tag = child.tag.lower() if isinstance(child.tag, str) else ""

                if tag == "break":
                    time_attr = child.get("time", "500ms")
                    ms = int(re.sub(r"[^\d]", "", time_attr) or "500")
                    pause_samples = int(ms / 1000 * _SAMPLE_RATE)
                    segments.append(np.zeros(pause_samples, dtype=np.float32))

                elif tag == "emphasis":
                    level = child.get("level", "moderate")
                    text_content = (child.text or "").strip()
                    if text_content:
                        audio, _ = self.synthesize(text_content, voice=voice)
                        gain = {"strong": 1.5, "moderate": 1.2, "reduced": 0.7}.get(level, 1.0)
                        audio = np.clip(audio * gain, -1.0, 1.0)
                        segments.append(audio)
                else:
                    _process_element(child)

                # Tail text
                if child.tail and child.tail.strip():
                    audio, _ = self.synthesize(child.tail.strip(), voice=voice)
                    segments.append(audio)

        _process_element(root)

        if not segments:
            return np.zeros(1, dtype=np.float32), _SAMPLE_RATE

        return np.concatenate(segments).astype(np.float32), _SAMPLE_RATE
