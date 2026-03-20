"""CLIP-based embedding service for cross-modal search."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
_CLAP_MODEL_NAME = "laion/clap-htsat-unfused"
_EMBEDDING_DIM = 512


class EmbeddingService:
    """Generate CLIP embeddings for images and text, CLAP embeddings for audio.

    Lazily loads the CLIP model on first use. Falls back to random
    embeddings (with a warning) when ``transformers`` is not installed.
    """

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._use_fallback = False
        self._clap_model = None
        self._clap_processor = None
        self._use_clap_fallback = False

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    def _load_clap_model(self) -> None:
        """Load CLAP model and processor, or activate fallback mode."""
        if self._clap_model is not None or self._use_clap_fallback:
            return

        try:
            from transformers import ClapModel, ClapProcessor

            logger.info("Loading CLAP model: %s", _CLAP_MODEL_NAME)
            self._clap_model = ClapModel.from_pretrained(_CLAP_MODEL_NAME)
            self._clap_processor = ClapProcessor.from_pretrained(_CLAP_MODEL_NAME)
            logger.info("CLAP model loaded successfully")
        except (ImportError, Exception):
            logger.warning(
                "CLAP model not available — using MFCC-based audio embedding fallback"
            )
            self._use_clap_fallback = True

    def _load_model(self) -> None:
        """Load CLIP model and processor, or activate fallback mode."""
        if self._model is not None or self._use_fallback:
            return

        try:
            from transformers import CLIPModel, CLIPProcessor

            logger.info("Loading CLIP model: %s", _CLIP_MODEL_NAME)
            self._model = CLIPModel.from_pretrained(_CLIP_MODEL_NAME)
            self._processor = CLIPProcessor.from_pretrained(_CLIP_MODEL_NAME)
            logger.info("CLIP model loaded successfully")
        except ImportError:
            logger.warning(
                "transformers library not available — using random embeddings as fallback. "
                "Install with: pip install transformers"
            )
            self._use_fallback = True

    # ------------------------------------------------------------------
    # Normalisation helper
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        """L2-normalise a vector (or batch of vectors)."""
        norm = np.linalg.norm(vector, axis=-1, keepdims=True)
        norm = np.where(norm == 0, 1, norm)
        return (vector / norm).astype(np.float32)

    # ------------------------------------------------------------------
    # Random fallback helpers
    # ------------------------------------------------------------------

    def _random_embedding(self) -> np.ndarray:
        vec = np.random.randn(_EMBEDDING_DIM).astype(np.float32)
        return self._normalize(vec)

    def _random_embeddings(self, n: int) -> np.ndarray:
        vecs = np.random.randn(n, _EMBEDDING_DIM).astype(np.float32)
        return self._normalize(vecs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_image(self, image: np.ndarray) -> np.ndarray:
        """Embed a single image → shape ``(512,)``."""
        self._load_model()

        if self._use_fallback:
            return self._random_embedding()

        import torch
        from PIL import Image as PILImage

        # Convert numpy BGR (OpenCV default) → RGB PIL
        if image.ndim == 3 and image.shape[2] == 3:
            image_rgb = image[:, :, ::-1]
        else:
            image_rgb = image
        pil_image = PILImage.fromarray(image_rgb.astype(np.uint8))

        inputs = self._processor(images=pil_image, return_tensors="pt")
        with torch.no_grad():
            features = self._model.get_image_features(**inputs)
        vec = features.squeeze().cpu().numpy().astype(np.float32)
        return self._normalize(vec)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string → shape ``(512,)``."""
        self._load_model()

        if self._use_fallback:
            return self._random_embedding()

        import torch

        inputs = self._processor(text=[text], return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            features = self._model.get_text_features(**inputs)
        vec = features.squeeze().cpu().numpy().astype(np.float32)
        return self._normalize(vec)

    def embed_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Embed an audio waveform → shape ``(512,)``.

        Tries CLAP model (``laion/clap-htsat-unfused``). If unavailable, falls
        back to MFCC-based embedding: 40 MFCCs → mean + std per coefficient →
        80 features → zero-pad to 512 → L2-normalise.
        """
        self._load_clap_model()

        if not self._use_clap_fallback:
            import torch

            # CLAP expects 48 kHz — resample if needed
            target_sr = 48000
            if sr != target_sr:
                duration = len(audio) / sr
                n_samples = int(duration * target_sr)
                indices = np.linspace(0, len(audio) - 1, n_samples)
                audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
                sr = target_sr

            inputs = self._clap_processor(
                audio=audio, sampling_rate=sr, return_tensors="pt"
            )
            with torch.no_grad():
                features = self._clap_model.get_audio_features(**inputs)
            vec = features.squeeze().cpu().numpy().astype(np.float32)
            # CLAP output may not be 512-dim; pad/truncate to 512
            if vec.shape[0] < _EMBEDDING_DIM:
                vec = np.pad(vec, (0, _EMBEDDING_DIM - vec.shape[0]))
            elif vec.shape[0] > _EMBEDDING_DIM:
                vec = vec[:_EMBEDDING_DIM]
            return self._normalize(vec)

        # ---- MFCC fallback ----
        return self._mfcc_embedding(audio, sr)

    def _mfcc_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """MFCC-based audio embedding fallback → shape ``(512,)``."""
        try:
            import librosa

            mfccs = librosa.feature.mfcc(y=audio.astype(np.float32), sr=sr, n_mfcc=40)
        except ImportError:
            # Ultra-minimal fallback: simple frame-based pseudo-MFCCs
            mfccs = self._simple_mfcc(audio, n_mfcc=40)

        # mean + std per coefficient → 80 features
        means = np.mean(mfccs, axis=1)  # (40,)
        stds = np.std(mfccs, axis=1)    # (40,)
        features = np.concatenate([means, stds])  # (80,)

        # Zero-pad to 512
        vec = np.zeros(_EMBEDDING_DIM, dtype=np.float32)
        vec[: len(features)] = features.astype(np.float32)

        return self._normalize(vec)

    @staticmethod
    def _simple_mfcc(audio: np.ndarray, n_mfcc: int = 40) -> np.ndarray:
        """Minimal MFCC-like features when librosa is unavailable."""
        audio = audio.astype(np.float64)
        frame_len = min(2048, len(audio))
        n_frames = max(1, len(audio) // frame_len)
        coeffs = np.zeros((n_mfcc, n_frames), dtype=np.float64)
        for i in range(n_frames):
            frame = audio[i * frame_len: (i + 1) * frame_len]
            spectrum = np.abs(np.fft.rfft(frame))[:n_mfcc]
            if len(spectrum) < n_mfcc:
                spectrum = np.pad(spectrum, (0, n_mfcc - len(spectrum)))
            coeffs[:, i] = np.log1p(spectrum)
        return coeffs

    def embed_batch_images(self, images: list[np.ndarray]) -> np.ndarray:
        """Embed a batch of images → shape ``(N, 512)``."""
        self._load_model()

        if self._use_fallback:
            return self._random_embeddings(len(images))

        import torch
        from PIL import Image as PILImage

        pil_images = []
        for img in images:
            if img.ndim == 3 and img.shape[2] == 3:
                img_rgb = img[:, :, ::-1]
            else:
                img_rgb = img
            pil_images.append(PILImage.fromarray(img_rgb.astype(np.uint8)))

        inputs = self._processor(images=pil_images, return_tensors="pt")
        with torch.no_grad():
            features = self._model.get_image_features(**inputs)
        vecs = features.cpu().numpy().astype(np.float32)
        return self._normalize(vecs)

    def embed_batch_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of text strings → shape ``(N, 512)``."""
        self._load_model()

        if self._use_fallback:
            return self._random_embeddings(len(texts))

        import torch

        inputs = self._processor(text=texts, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            features = self._model.get_text_features(**inputs)
        vecs = features.cpu().numpy().astype(np.float32)
        return self._normalize(vecs)
