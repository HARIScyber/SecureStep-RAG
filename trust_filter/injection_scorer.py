"""Prompt injection scorer with hybrid rule and embedding checks."""

from __future__ import annotations

import re
from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.embedding_loader import EmbeddingLoader
from pipeline.retriever import RetrievedDocument


class InjectionScorer:
    """Scores how likely a document contains prompt injection payloads.

    Returns 0-100 where lower score means more suspicious.
    """

    IMPERATIVE_PATTERNS = [
        r"\bignore\b",
        r"\bdisregard\b",
        r"\bforget\b",
        r"\bpretend\b",
        r"\boutput\b",
        r"\breveal\b",
    ]
    FAKE_SYSTEM_PATTERNS = [
        r"\bSYSTEM:\b",
        r"\[INST\]",
        r"<\|im_start\|>",
        r"<\|system\|>",
    ]
    REDIRECT_PATTERNS = [
        r"\bsearch for\b",
        r"\bretrieve document\b",
        r"\bquery for\b",
        r"\bnext hop\b",
    ]

    def __init__(self, max_penalty: float = 80.0) -> None:
        self.max_penalty = max_penalty
        self.embedder = EmbeddingLoader().load()

    def _count_matches(self, text: str, patterns: List[str]) -> int:
        return sum(1 for p in patterns if re.search(p, text, flags=re.IGNORECASE))

    def _embedding_anomaly_penalty(self, query: str, content: str) -> float:
        """Embedding-based anomaly: low query-doc similarity indicates hidden redirection."""

        query_vec = np.array(self.embedder.embed_query(query), dtype=float).reshape(1, -1)
        doc_vec = np.array(self.embedder.embed_query(content[:2500]), dtype=float).reshape(1, -1)
        sim = float(cosine_similarity(query_vec, doc_vec)[0][0])

        # Map low semantic alignment to a bounded penalty.
        if sim >= 0.75:
            return 0.0
        if sim >= 0.55:
            return 8.0
        if sim >= 0.35:
            return 15.0
        return 25.0

    def _hop_redirect_penalty(self, content: str, hop_history: List[str]) -> float:
        if not hop_history:
            return 0.0

        latest_hop = hop_history[-1].lower()
        content_lower = content.lower()
        redirect_markers = ["instead", "do not answer", "new query", "alternate query"]

        marker_hit = any(marker in content_lower for marker in redirect_markers)
        lexical_shift_hint = any(term in content_lower and term not in latest_hop for term in ["password", "credential", "secret", "admin"])

        if marker_hit and lexical_shift_hint:
            return 15.0
        if marker_hit:
            return 8.0
        return 0.0

    def score(self, query: str, doc: RetrievedDocument, hop_history: List[str]) -> float:
        """Return trust-aligned safety score in 0-100 (higher is safer)."""

        text = doc.content.strip()
        if not text:
            return 0.0

        imperative_hits = self._count_matches(text, self.IMPERATIVE_PATTERNS)
        fake_system_hits = self._count_matches(text, self.FAKE_SYSTEM_PATTERNS)
        redirect_hits = self._count_matches(text, self.REDIRECT_PATTERNS)

        penalty = 0.0
        penalty += imperative_hits * 10.0
        penalty += fake_system_hits * 20.0
        penalty += redirect_hits * 14.0
        penalty += self._embedding_anomaly_penalty(query=query, content=text)
        penalty += self._hop_redirect_penalty(content=text, hop_history=hop_history)

        if bool(doc.metadata.get("adversarial", False)):
            penalty += 18.0

        bounded_penalty = min(self.max_penalty, penalty)
        score = 100.0 - bounded_penalty
        return max(0.0, min(100.0, score))
