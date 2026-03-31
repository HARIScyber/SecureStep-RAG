"""Cross-hop consistency scorer based on context centroid similarity."""

from __future__ import annotations

from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.embedding_loader import EmbeddingLoader
from pipeline.retriever import RetrievedDocument


class HopScorer:
    """Scores whether a doc is consistent with accepted docs from earlier hops."""

    def __init__(self) -> None:
        self.embedder = EmbeddingLoader().load()

    def score(self, doc: RetrievedDocument, accepted_docs: List[RetrievedDocument]) -> float:
        if not accepted_docs:
            return 80.0

        accepted_vectors = np.array(
            self.embedder.embed_documents([d.content[:2000] for d in accepted_docs]),
            dtype=float,
        )
        centroid = accepted_vectors.mean(axis=0).reshape(1, -1)
        doc_vec = np.array(self.embedder.embed_query(doc.content[:2000]), dtype=float).reshape(1, -1)

        sim = float(cosine_similarity(doc_vec, centroid)[0][0])
        normalized = (sim + 1.0) / 2.0
        return max(0.0, min(100.0, normalized * 100.0))
