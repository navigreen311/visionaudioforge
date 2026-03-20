"""FAISS vector index service for approximate nearest-neighbour search."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss

    _FAISS_AVAILABLE = True
except ImportError:
    faiss = None  # type: ignore[assignment]
    _FAISS_AVAILABLE = False
    logger.warning(
        "faiss-cpu not installed — FAISSIndexService will not function. "
        "Install with: pip install faiss-cpu"
    )


class FAISSIndexService:
    """Manage a FAISS index with string ID mapping."""

    def __init__(self, dimension: int = 512) -> None:
        self.dimension = dimension
        self.index = None
        self.id_map: dict[int, str] = {}  # FAISS internal idx → asset_id
        self._index_type: str = "none"
        self._next_idx: int = 0

    # ------------------------------------------------------------------
    # Index lifecycle
    # ------------------------------------------------------------------

    def create_index(self, index_type: str = "flat") -> None:
        """Create a new FAISS index.

        Args:
            index_type: ``'flat'`` for exact search (IndexFlatIP) or
                        ``'ivf'`` for approximate search (IndexIVFFlat).
        """
        if not _FAISS_AVAILABLE:
            raise RuntimeError("faiss-cpu is not installed")

        if index_type == "flat":
            self.index = faiss.IndexFlatIP(self.dimension)
        elif index_type == "ivf":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100, faiss.METRIC_INNER_PRODUCT)
        else:
            raise ValueError(f"Unknown index_type: {index_type!r}. Use 'flat' or 'ivf'.")

        self._index_type = index_type
        self.id_map = {}
        self._next_idx = 0
        logger.info("Created FAISS %s index (dim=%d)", index_type, self.dimension)

    # ------------------------------------------------------------------
    # Vector operations
    # ------------------------------------------------------------------

    def add_vectors(self, vectors: np.ndarray, ids: list[str]) -> int:
        """Add vectors with associated string IDs.

        Returns:
            Number of vectors successfully added.
        """
        if self.index is None:
            raise RuntimeError("Index not created. Call create_index() first.")

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension {vectors.shape[1]} does not match index dimension {self.dimension}"
            )

        # For IVF index, must be trained first
        if self._index_type == "ivf" and not self.index.is_trained:
            logger.info("Training IVF index with %d vectors", vectors.shape[0])
            self.index.train(vectors)

        self.index.add(vectors)

        for asset_id in ids:
            self.id_map[self._next_idx] = asset_id
            self._next_idx += 1

        logger.debug("Added %d vectors (total: %d)", len(ids), self.index.ntotal)
        return len(ids)

    def search(self, query_vector: np.ndarray, k: int = 10) -> list[dict]:
        """Search for the *k* nearest neighbours.

        Returns:
            List of ``{"asset_id": str, "score": float, "rank": int}``.
        """
        if self.index is None:
            raise RuntimeError("Index not created. Call create_index() first.")

        query = np.ascontiguousarray(query_vector, dtype=np.float32).reshape(1, self.dimension)
        actual_k = min(k, self.index.ntotal)
        if actual_k == 0:
            return []

        scores, indices = self.index.search(query, actual_k)

        results: list[dict] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
            if idx == -1:
                continue
            asset_id = self.id_map.get(int(idx), f"unknown-{idx}")
            results.append({"asset_id": asset_id, "score": float(score), "rank": rank})
        return results

    def remove_vectors(self, ids: list[str]) -> None:
        """Remove vectors by ID — **not supported** in basic FAISS indexes."""
        logger.warning(
            "remove_vectors() is not supported in basic FAISS indexes. "
            "Rebuild the index to remove vectors. Requested IDs: %s",
            ids,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_index(self, path: str) -> None:
        """Save the FAISS index and ID map to disk."""
        if self.index is None:
            raise RuntimeError("No index to save.")

        index_path = Path(path)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_path))

        id_map_path = index_path.with_suffix(".idmap.json")
        with open(id_map_path, "w") as f:
            json.dump(
                {"id_map": {str(k): v for k, v in self.id_map.items()}, "next_idx": self._next_idx, "index_type": self._index_type},
                f,
            )
        logger.info("Saved index to %s", path)

    def load_index(self, path: str) -> None:
        """Load a FAISS index and ID map from disk."""
        if not _FAISS_AVAILABLE:
            raise RuntimeError("faiss-cpu is not installed")

        index_path = Path(path)
        self.index = faiss.read_index(str(index_path))
        self.dimension = self.index.d

        id_map_path = index_path.with_suffix(".idmap.json")
        if id_map_path.exists():
            with open(id_map_path) as f:
                data = json.load(f)
            self.id_map = {int(k): v for k, v in data["id_map"].items()}
            self._next_idx = data.get("next_idx", max(self.id_map.keys(), default=-1) + 1)
            self._index_type = data.get("index_type", "flat")
        else:
            logger.warning("ID map file not found at %s — id_map will be empty", id_map_path)

        logger.info("Loaded index from %s (ntotal=%d)", path, self.index.ntotal)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return index statistics."""
        if self.index is None:
            return {
                "total_vectors": 0,
                "dimension": self.dimension,
                "index_type": self._index_type,
                "is_trained": False,
            }
        return {
            "total_vectors": int(self.index.ntotal),
            "dimension": self.dimension,
            "index_type": self._index_type,
            "is_trained": bool(self.index.is_trained),
        }
