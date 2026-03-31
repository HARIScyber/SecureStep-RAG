"""Source credibility scorer from document metadata."""

from __future__ import annotations

from pipeline.retriever import RetrievedDocument


class SourceScorer:
    """Maps source metadata to a trust score between 0 and 100."""

    SOURCE_TYPE_PRIOR = {
        "official": 0.95,
        "paper": 0.9,
        "internal": 0.85,
        "web": 0.65,
        "forum": 0.45,
        "unknown": 0.4,
    }

    def score(self, doc: RetrievedDocument) -> float:
        source_type = str(doc.metadata.get("source_type", "unknown")).lower()
        prior = self.SOURCE_TYPE_PRIOR.get(source_type, 0.4)
        credibility = float(doc.metadata.get("credibility", 0.5))

        adversarial = bool(doc.metadata.get("adversarial", False))
        if adversarial:
            credibility = min(credibility, 0.2)

        final = (0.6 * prior) + (0.4 * credibility)
        return max(0.0, min(100.0, final * 100.0))
