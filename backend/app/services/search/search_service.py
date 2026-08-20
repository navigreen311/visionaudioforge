"""High-level cross-modal search service orchestrating embeddings, FAISS, and the database."""

from __future__ import annotations

import io
import logging
import time
import uuid
from typing import Any

import numpy as np

from app.services.search.embeddings import EmbeddingService
from app.services.search.faiss_index import FAISSIndexService

logger = logging.getLogger(__name__)


class CrossModalSearchService:
    """Orchestrate embedding generation, FAISS indexing, and DB metadata."""

    def __init__(
        self,
        embedding_svc: EmbeddingService,
        index_svc: FAISSIndexService,
        db_session: Any = None,
    ) -> None:
        self.embedding_svc = embedding_svc
        self.index_svc = index_svc
        self.db = db_session

        # Ensure an index exists
        if self.index_svc.index is None:
            self.index_svc.create_index("flat")

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def index_asset(
        self, asset_id: str, modality: str, file_data: bytes
    ) -> dict:
        """Generate an embedding for an asset and add it to the FAISS index.

        Args:
            asset_id: Unique asset identifier.
            modality: ``'image'`` or ``'audio'`` (audio treated as spectrogram image).
            file_data: Raw file bytes.

        Returns:
            ``{"asset_id": str, "embedded": bool}``
        """
        try:
            if modality == "image":
                image = self._bytes_to_image(file_data)
                vector = self.embedding_svc.embed_image(image)
            elif modality == "audio":
                # For audio, convert to mel-spectrogram image then embed
                image = self._audio_bytes_to_spectrogram(file_data)
                vector = self.embedding_svc.embed_image(image)
            else:
                logger.warning("Unsupported modality %r for asset %s", modality, asset_id)
                return {"asset_id": asset_id, "embedded": False}

            vector = vector.reshape(1, -1)
            self.index_svc.add_vectors(vector, [asset_id])

            # Persist embedding record to DB if session is available
            if self.db is not None:
                await self._store_embedding_record(asset_id, modality, vector.squeeze())

            logger.info("Indexed asset %s (modality=%s)", asset_id, modality)
            return {"asset_id": asset_id, "embedded": True}

        except Exception:
            logger.exception("Failed to index asset %s", asset_id)
            return {"asset_id": asset_id, "embedded": False}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_by_text(
        self, query: str, k: int = 10, modality_filter: str | None = None
    ) -> list[dict]:
        """Embed a text query and search the FAISS index."""
        t0 = time.perf_counter()
        query_vec = self.embedding_svc.embed_text(query)
        raw_results = self.index_svc.search(query_vec, k=k)
        results = await self._enrich_results(raw_results, modality_filter)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("search_by_text(%r) → %d results in %.1f ms", query, len(results), elapsed)
        return results

    async def search_by_image(self, image_data: bytes, k: int = 10) -> list[dict]:
        """Embed an uploaded image and search the FAISS index."""
        image = self._bytes_to_image(image_data)
        query_vec = self.embedding_svc.embed_image(image)
        raw_results = self.index_svc.search(query_vec, k=k)
        return await self._enrich_results(raw_results)

    async def search_similar(self, asset_id: str, k: int = 10) -> list[dict]:
        """Find assets similar to an already-indexed asset."""
        # Look up existing embedding in the index by searching for the asset_id
        # We need to find the vector for this asset in the index
        faiss_idx = None
        for idx, aid in self.index_svc.id_map.items():
            if aid == asset_id:
                faiss_idx = idx
                break

        if faiss_idx is None:
            logger.warning("Asset %s not found in FAISS index", asset_id)
            return []

        # Reconstruct the vector from the FAISS index
        try:
            vector = np.zeros(self.index_svc.dimension, dtype=np.float32)
            self.index_svc.index.reconstruct(faiss_idx, vector)
        except RuntimeError:
            logger.warning("Cannot reconstruct vector for asset %s (index type may not support it)", asset_id)
            return []

        raw_results = self.index_svc.search(vector, k=k + 1)
        # Exclude the query asset itself
        results = [r for r in raw_results if r["asset_id"] != asset_id][:k]
        # Re-rank
        for i, r in enumerate(results, start=1):
            r["rank"] = i
        return await self._enrich_results(results)

    async def rebuild_index(self, workspace_id: str | None = None) -> dict:
        """Rebuild the entire FAISS index from stored assets.

        In a full implementation this would iterate over all assets in the DB,
        re-embed them, and rebuild the index from scratch. For now, returns
        the current index stats.
        """
        logger.info("rebuild_index called (workspace_id=%s)", workspace_id)
        # Reset index
        self.index_svc.create_index("flat")
        # In production: iterate DB assets, embed each, add to index
        return self.index_svc.get_stats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bytes_to_image(data: bytes) -> np.ndarray:
        """Convert raw bytes to a numpy image array."""
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(data)).convert("RGB")
        return np.array(img, dtype=np.uint8)

    @staticmethod
    def _audio_bytes_to_spectrogram(data: bytes) -> np.ndarray:
        """Convert audio bytes to a mel-spectrogram image for CLIP embedding."""
        try:
            import librosa
            import soundfile as sf

            audio_array, sr = sf.read(io.BytesIO(data))
            if audio_array.ndim > 1:
                audio_array = audio_array.mean(axis=1)
            mel = librosa.feature.melspectrogram(y=audio_array.astype(np.float32), sr=sr)
            mel_db = librosa.power_to_db(mel, ref=np.max)
            # Normalise to 0-255 and convert to 3-channel image
            mel_norm = ((mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8) * 255).astype(np.uint8)
            mel_rgb = np.stack([mel_norm] * 3, axis=-1)
            return mel_rgb
        except ImportError as exc:
            # This used to return `np.random.randint(0, 255, (224, 224, 3))` and
            # log a warning. The caller embeds whatever comes back and stores it
            # in the vector index, so a missing dependency quietly filled the
            # index with embeddings of noise - permanently, and indistinguishably
            # from real ones. Every later similarity search then ranked against
            # them. Refusing costs one failed upload; the placeholder cost the
            # index's trustworthiness with no signal that anything was wrong.
            logger.error(
                "cannot build a spectrogram: librosa/soundfile missing (%s)", exc
            )
            raise RuntimeError(
                "Audio embedding requires librosa and soundfile, which are not "
                "installed. Refusing to index audio rather than store a "
                "placeholder embedding."
            ) from exc

    async def _store_embedding_record(
        self, asset_id: str, modality: str, vector: np.ndarray
    ) -> None:
        """Persist an embedding record in the database."""
        try:
            from app.models.embedding import Embedding

            record = Embedding(
                source_type=modality,
                source_id=uuid.UUID(asset_id) if isinstance(asset_id, str) else asset_id,
                model_name="openai/clip-vit-base-patch32",
                vector_data=vector.tolist(),
                workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            )
            self.db.add(record)
            await self.db.commit()
        except Exception:
            logger.exception("Failed to store embedding record for asset %s", asset_id)

    async def _enrich_results(
        self, raw_results: list[dict], modality_filter: str | None = None
    ) -> list[dict]:
        """Enrich FAISS results with asset metadata from the DB.

        When no DB session is available, returns results with placeholder metadata.
        """
        enriched: list[dict] = []
        for r in raw_results:
            result = {
                "asset_id": r["asset_id"],
                "score": r["score"],
                "rank": r["rank"],
                "asset_type": "unknown",
                "filename": "",
                "path": "",
            }

            if self.db is not None:
                try:
                    from sqlalchemy import select
                    from app.models.asset import Asset

                    stmt = select(Asset).where(Asset.id == uuid.UUID(r["asset_id"]))
                    db_result = await self.db.execute(stmt)
                    asset = db_result.scalar_one_or_none()
                    if asset:
                        result["asset_type"] = asset.media_type
                        result["filename"] = asset.filename
                        result["path"] = asset.storage_path
                except Exception:
                    pass  # Use placeholder metadata

            if modality_filter and result["asset_type"] != modality_filter:
                continue

            enriched.append(result)

        return enriched
