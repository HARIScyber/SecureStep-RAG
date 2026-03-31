"""Confidence gate that decides whether another retrieval hop is needed."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

from pipeline.retriever import RetrievedDocument
from trust_filter.filter import TrustScore


class ConfidenceGate:
    """Computes confidence from trust and context coverage signals."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[1]
        cfg_path = config_path or (base / "configs" / "pipeline.yml")
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        c = cfg["pipeline"]["confidence"]
        self.base = float(c["base"])
        self.trust_weight = float(c["trust_component_weight"])
        self.context_weight = float(c["context_component_weight"])

    def compute(
        self,
        query: str,
        accepted_docs: List[RetrievedDocument],
        trust_scores: List[TrustScore],
        hop_count: int,
        max_hops: int,
    ) -> float:
        del query
        if not trust_scores:
            return max(0.0, self.base - 20.0)

        avg_trust = sum(score.total for score in trust_scores) / len(trust_scores)
        context_gain = min(1.0, len(accepted_docs) / 4.0) * 100.0
        hop_pressure = (hop_count / max(max_hops, 1)) * 10.0

        confidence = (
            self.base
            + avg_trust * self.trust_weight
            + context_gain * self.context_weight
            + hop_pressure
        )
        return max(0.0, min(100.0, confidence))
