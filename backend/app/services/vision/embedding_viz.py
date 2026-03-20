"""Embedding visualization: dimensionality reduction, clustering, and plotting."""

from __future__ import annotations

import base64
import io
import logging

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingVisualizer:
    """Visualize high-dimensional embeddings via reduction, clustering, and plots."""

    @staticmethod
    def reduce_dimensions(
        embeddings: np.ndarray,
        method: str = "tsne",
        n_components: int = 2,
    ) -> np.ndarray:
        """Reduce embedding dimensionality for visualization.

        Args:
            embeddings: Array of shape (N, D) with N samples, D dimensions.
            method: Reduction method - 'tsne', 'umap', or 'pca'.
            n_components: Target dimensionality (default 2).

        Returns:
            Array of shape (N, n_components).
        """
        if method == "tsne":
            from sklearn.manifold import TSNE

            perplexity = min(30.0, max(1.0, float(len(embeddings) - 1)))
            reducer = TSNE(
                n_components=n_components,
                perplexity=perplexity,
                random_state=42,
            )
            return reducer.fit_transform(embeddings)

        elif method == "umap":
            try:
                import umap  # type: ignore[import-untyped]

                reducer = umap.UMAP(
                    n_components=n_components, random_state=42,
                )
                return reducer.fit_transform(embeddings)
            except ImportError:
                logger.warning("umap-learn not installed, falling back to PCA.")
                from sklearn.decomposition import PCA

                reducer = PCA(n_components=n_components, random_state=42)
                return reducer.fit_transform(embeddings)

        elif method == "pca":
            from sklearn.decomposition import PCA

            reducer = PCA(n_components=n_components, random_state=42)
            return reducer.fit_transform(embeddings)

        else:
            raise ValueError(f"Unknown reduction method: {method!r}. Use 'tsne', 'umap', or 'pca'.")

    @staticmethod
    def plot_embeddings(
        reduced: np.ndarray,
        labels: list | np.ndarray | None = None,
        title: str = "Embedding Space",
    ) -> str:
        """Create a scatter plot of reduced embeddings and return as base64 PNG.

        Args:
            reduced: Array of shape (N, 2) with reduced coordinates.
            labels: Optional labels for coloring points.
            title: Plot title.

        Returns:
            Base64-encoded PNG string.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6))

        if labels is not None:
            labels_arr = np.asarray(labels)
            unique_labels = np.unique(labels_arr)
            for label in unique_labels:
                mask = labels_arr == label
                ax.scatter(
                    reduced[mask, 0],
                    reduced[mask, 1],
                    label=str(label),
                    alpha=0.7,
                    s=20,
                )
            ax.legend(loc="best", fontsize=8)
        else:
            ax.scatter(reduced[:, 0], reduced[:, 1], alpha=0.7, s=20)

        ax.set_title(title)
        ax.set_xlabel("Component 1")
        ax.set_ylabel("Component 2")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    @staticmethod
    def cluster_embeddings(
        embeddings: np.ndarray,
        method: str = "kmeans",
        n_clusters: int = 5,
    ) -> dict:
        """Cluster embeddings and return labels, centroids, and quality score.

        Args:
            embeddings: Array of shape (N, D).
            method: Clustering method ('kmeans').
            n_clusters: Number of clusters.

        Returns:
            dict with labels (list), centroids (ndarray), and silhouette_score (float).
        """
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        # Ensure n_clusters doesn't exceed sample count
        n_samples = len(embeddings)
        n_clusters = min(n_clusters, n_samples)

        if n_clusters < 2:
            return {
                "labels": [0] * n_samples,
                "centroids": np.mean(embeddings, axis=0, keepdims=True),
                "silhouette_score": 0.0,
            }

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        score = float(silhouette_score(embeddings, labels))

        return {
            "labels": labels.tolist(),
            "centroids": kmeans.cluster_centers_,
            "silhouette_score": round(score, 4),
        }
