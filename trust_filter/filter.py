"""Main trust filter that combines all trust signals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from pipeline.retriever import RetrievedDocument
from trust_filter.hop_scorer import HopScorer
from trust_filter.injection_scorer import InjectionScorer
from trust_filter.semantic_scorer import SemanticScorer
from trust_filter.source_scorer import SourceScorer


class TrustScore(BaseModel):
    """Trust score breakdown per document."""

    semantic: float = Field(ge=0.0, le=100.0)
    source: float = Field(ge=0.0, le=100.0)
    injection: float = Field(ge=0.0, le=100.0)
    hop: float = Field(ge=0.0, le=100.0)
    total: float = Field(ge=0.0, le=100.0)


@dataclass
class TrustWeights:
    """Weighting for trust score components."""

    semantic: float
    source: float
    injection: float
    hop: float


class TrustFilter:
    """Scores retrieved documents and decides whether they are trustworthy enough."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        cfg = self._load_config(config_path)
        self.threshold = float(cfg["pipeline"]["trust_threshold"])
        weight_cfg = cfg["pipeline"]["trust_weights"]

        self.weights = TrustWeights(
            semantic=float(weight_cfg["semantic"]),
            source=float(weight_cfg["source"]),
            injection=float(weight_cfg["injection"]),
            hop=float(weight_cfg["hop"]),
        )

        self.semantic_scorer = SemanticScorer()
        self.source_scorer = SourceScorer()
        self.injection_scorer = InjectionScorer()
        self.hop_scorer = HopScorer()

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        base = Path(__file__).resolve().parents[1]
        cfg_path = config_path or (base / "configs" / "pipeline.yml")
        with cfg_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def score(
        self,
        doc: RetrievedDocument,
        query: str,
        hop_history: List[str],
        accepted_docs: Optional[List[RetrievedDocument]] = None,
    ) -> TrustScore:
        """Score a document on trust signals and return the aggregate score."""

        semantic = self.semantic_scorer.score(query=query, doc=doc)
        source = self.source_scorer.score(doc=doc)
        injection = self.injection_scorer.score(query=query, doc=doc, hop_history=hop_history)
        hop = self.hop_scorer.score(doc=doc, accepted_docs=accepted_docs or [])

        weighted = (
            semantic * self.weights.semantic
            + source * self.weights.source
            + injection * self.weights.injection
            + hop * self.weights.hop
        )
        total = max(0.0, min(100.0, weighted))

        return TrustScore(
            semantic=semantic,
            source=source,
            injection=injection,
            hop=hop,
            total=total,
        )

    def is_trusted(self, trust_score: TrustScore) -> bool:
        """Check if trust score passes configured threshold."""

        return trust_score.total >= self.threshold
