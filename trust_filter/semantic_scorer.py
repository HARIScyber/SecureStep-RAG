"""Semantic relevance scorer using query-doc cosine similarity."""

from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.embedding_loader import EmbeddingLoader
from pipeline.retriever import RetrievedDocument


class SemanticScorer:
    """Scores query-document semantic alignment on a 0-100 scale."""

    def __init__(self) -> None:
        self.embedder = EmbeddingLoader().load()

    def score(self, query: str, doc: RetrievedDocument) -> float:
        q = np.array(self.embedder.embed_query(query), dtype=float).reshape(1, -1)
        d = np.array(self.embedder.embed_query(doc.content[:2500]), dtype=float).reshape(1, -1)
        sim = float(cosine_similarity(q, d)[0][0])
        normalized = (sim + 1.0) / 2.0
        return max(0.0, min(100.0, normalized * 100.0))
