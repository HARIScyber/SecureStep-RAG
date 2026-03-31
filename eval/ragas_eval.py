"""RAGAS-style scoring helpers for hop-aware evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class RagasMetrics:
    faithfulness: float
    context_recall: float


def evaluate_hop(
    answer: str,
    context_chunks: List[str],
    reference_keywords: List[str],
) -> RagasMetrics:
    """Approximate faithfulness/context recall when full RAGAS runtime is unavailable."""

    if not context_chunks:
        return RagasMetrics(faithfulness=0.0, context_recall=0.0)

    joined_context = " ".join(context_chunks).lower()
    answer_l = answer.lower()

    supported_terms = sum(1 for token in answer_l.split() if token in joined_context)
    faithfulness = min(100.0, (supported_terms / max(len(answer_l.split()), 1)) * 100.0)

    keyword_hits = sum(1 for kw in reference_keywords if kw.lower() in joined_context)
    context_recall = min(100.0, (keyword_hits / max(len(reference_keywords), 1)) * 100.0)

    return RagasMetrics(faithfulness=faithfulness, context_recall=context_recall)
