"""Semantic drift detection for hop-to-hop query progression."""

from __future__ import annotations

from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.embedding_loader import EmbeddingLoader


class DriftDetector:
    """Detects semantic drift between consecutive hop queries."""

    def __init__(self) -> None:
        self.embedder = EmbeddingLoader().load()

    def drift_score(self, hop_queries: List[str]) -> float:
        if len(hop_queries) < 2:
            return 0.0

        prev = np.array(self.embedder.embed_query(hop_queries[-2]), dtype=float).reshape(1, -1)
        curr = np.array(self.embedder.embed_query(hop_queries[-1]), dtype=float).reshape(1, -1)
        sim = float(cosine_similarity(prev, curr)[0][0])

        drift = 1.0 - ((sim + 1.0) / 2.0)
        return max(0.0, min(100.0, drift * 100.0))
