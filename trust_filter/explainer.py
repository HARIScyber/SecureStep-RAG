"""Human-readable explanations for trust filter verdicts.

Generates natural language explanations for why documents are blocked or accepted,
integrating with all trust signal scorers. Used by dashboard Trust Inspector and
audit logs for enterprise observability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.embedding_loader import EmbeddingLoader
from pipeline.retriever import RetrievedDocument
from trust_filter.filter import TrustScore
from trust_filter.injection_scorer import InjectionScorer
from trust_filter.hop_scorer import HopScorer
from trust_filter.semantic_scorer import SemanticScorer
from trust_filter.source_scorer import SourceScorer


class Verdict(str, Enum):
    """Trust filter verdict."""

    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    SUSPICIOUS = "SUSPICIOUS"


@dataclass
class SignalBreakdown:
    """Detailed breakdown of each trust signal."""

    semantic_score: float
    semantic_reason: str
    source_score: float
    source_reason: str
    injection_score: float
    injection_reason: str
    hop_score: float
    hop_reason: str


@dataclass
class BlockExplanation:
    """Human-readable explanation for a trust filter verdict.

    Used by dashboard Trust Inspector and audit logs.
    """

    verdict: Verdict
    primary_reason: str
    signal_breakdown: SignalBreakdown
    triggered_rules: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-100, how certain is this verdict
    recommendation: str = ""

    def as_dict(self) -> Dict:
        """Serialize to dictionary for JSON API."""
        return {
            "verdict": self.verdict.value,
            "primary_reason": self.primary_reason,
            "signal_breakdown": {
                "semantic_score": self.signal_breakdown.semantic_score,
                "semantic_reason": self.signal_breakdown.semantic_reason,
                "source_score": self.signal_breakdown.source_score,
                "source_reason": self.signal_breakdown.source_reason,
                "injection_score": self.signal_breakdown.injection_score,
                "injection_reason": self.signal_breakdown.injection_reason,
                "hop_score": self.signal_breakdown.hop_score,
                "hop_reason": self.signal_breakdown.hop_reason,
            },
            "triggered_rules": self.triggered_rules,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
        }

    def as_markdown(self) -> str:
        """Format explanation as markdown for notebook display.

        Returns:
            Formatted markdown string with all explanation details.
        """
        lines = [
            f"# Trust Filter Verdict: {self.verdict.value}",
            f"**Confidence:** {self.confidence:.0f}%",
            "",
            f"## Primary Reason",
            self.primary_reason,
            "",
            f"## Signal Scores",
            f"- **Semantic Relevance:** {self.signal_breakdown.semantic_score:.1f}/100 — {self.signal_breakdown.semantic_reason}",
            f"- **Source Credibility:** {self.signal_breakdown.source_score:.1f}/100 — {self.signal_breakdown.source_reason}",
            f"- **Injection Risk:** {self.signal_breakdown.injection_score:.1f}/100 — {self.signal_breakdown.injection_reason}",
            f"- **Hop Consistency:** {self.signal_breakdown.hop_score:.1f}/100 — {self.signal_breakdown.hop_reason}",
            "",
        ]

        if self.triggered_rules:
            lines.extend([
                "## Triggered Rules",
                *[f"- {rule}" for rule in self.triggered_rules],
                "",
            ])

        if self.recommendation:
            lines.extend([
                "## Recommendation",
                self.recommendation,
                "",
            ])

        return "\n".join(lines)


class TrustExplainer:
    """Generates human-readable explanations for trust verdicts."""

    def __init__(self) -> None:
        """Initialize explainer with all scorer components."""
        self.semantic_scorer = SemanticScorer()
        self.source_scorer = SourceScorer()
        self.injection_scorer = InjectionScorer()
        self.hop_scorer = HopScorer()
        self.embedder = EmbeddingLoader().load()

    def explain(
        self,
        doc: RetrievedDocument,
        trust_score: TrustScore,
        query: str,
        threshold: float = 60.0,
        hop_history: Optional[List[str]] = None,
        accepted_docs: Optional[List[RetrievedDocument]] = None,
    ) -> BlockExplanation:
        """Generate explanation for why document was blocked or accepted.

        Args:
            doc: Retrieved document being scored
            trust_score: Trust score breakdown from TrustFilter.score()
            query: User query
            threshold: Trust threshold for passing (default 60.0)
            hop_history: List of previous hop queries for context
            accepted_docs: Previously accepted documents from earlier hops

        Returns:
            BlockExplanation with natural language verdict and reasoning
        """
        hop_history = hop_history or []
        accepted_docs = accepted_docs or []

        # Determine verdict
        passed = trust_score.total >= threshold
        verdict = Verdict.PASSED if passed else Verdict.BLOCKED

        # Detect triggered rules from injection scorer
        triggered_rules = self._detect_triggered_rules(doc, query, hop_history)

        # Build signal breakdown with explanations
        signal_breakdown = self._build_signal_breakdown(
            trust_score, doc, query, hop_history, accepted_docs
        )

        # Generate primary reason (most damaging signal)
        primary_reason = self._get_primary_reason(trust_score, signal_breakdown, triggered_rules)

        # Compute confidence in verdict
        confidence = self._compute_confidence(trust_score, triggered_rules, passed)

        # Generate recommendation
        recommendation = self._get_recommendation(verdict, trust_score, triggered_rules)

        return BlockExplanation(
            verdict=verdict,
            primary_reason=primary_reason,
            signal_breakdown=signal_breakdown,
            triggered_rules=triggered_rules,
            confidence=confidence,
            recommendation=recommendation,
        )

    def _detect_triggered_rules(
        self, doc: RetrievedDocument, query: str, hop_history: List[str]
    ) -> List[str]:
        """Detect which specific injection rules fired.

        Args:
            doc: Document to analyze
            query: User query
            hop_history: Previous hop queries

        Returns:
            List of human-readable triggered rule descriptions
        """
        triggered = []
        content = doc.content.lower()
        query_lower = query.lower()

        # Check imperative patterns
        for pattern in self.injection_scorer.IMPERATIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                verb = pattern.replace(r"\b", "").strip()
                if re.match(r"^[a-z]+$", verb):
                    triggered.append(f"imperative_verb_detected('{verb}')")

        # Check fake system patterns
        for pattern in self.injection_scorer.FAKE_SYSTEM_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                display_pattern = pattern.replace(r"\b", "").replace(r"\\", "")
                triggered.append(f"fake_system_prompt_pattern('{display_pattern}')")

        # Check redirect patterns
        for pattern in self.injection_scorer.REDIRECT_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                display_pattern = pattern.strip(r"\b").replace(r"\b", "")
                triggered.append(f"redirect_verb_detected('{display_pattern}')")

        # Check embedding anomaly
        embedding_penalty = self.injection_scorer._embedding_anomaly_penalty(query, doc.content)
        if embedding_penalty > 0:
            triggered.append(
                f"embedding_anomaly(query_similarity_low, penalty={embedding_penalty:.0f})"
            )

        # Check hop redirect
        if hop_history:
            hop_penalty = self.injection_scorer._hop_redirect_penalty(content, hop_history)
            if hop_penalty > 0:
                latest_hop = hop_history[-1]
                triggered.append(f"hop_redirect_detected(latest_hop='{latest_hop[:30]}...', penalty={hop_penalty:.0f})")

        return triggered

    def _build_signal_breakdown(
        self,
        trust_score: TrustScore,
        doc: RetrievedDocument,
        query: str,
        hop_history: List[str],
        accepted_docs: List[RetrievedDocument],
    ) -> SignalBreakdown:
        """Build detailed explanation for each trust signal.

        Args:
            trust_score: TrustScore breakdown
            doc: Retrieved document
            query: User query
            hop_history: Previous hop queries
            accepted_docs: Previously accepted documents

        Returns:
            SignalBreakdown with score and reason for each signal
        """
        # Semantic signal
        semantic_reason = self._explain_semantic(
            trust_score.semantic, query, doc.content
        )

        # Source signal
        source_reason = self._explain_source(trust_score.source, doc.metadata)

        # Injection signal
        injection_reason = self._explain_injection(
            trust_score.injection, doc.content, query, hop_history
        )

        # Hop signal
        hop_reason = self._explain_hop(trust_score.hop, doc, accepted_docs)

        return SignalBreakdown(
            semantic_score=trust_score.semantic,
            semantic_reason=semantic_reason,
            source_score=trust_score.source,
            source_reason=source_reason,
            injection_score=trust_score.injection,
            injection_reason=injection_reason,
            hop_score=trust_score.hop,
            hop_reason=hop_reason,
        )

    def _explain_semantic(self, score: float, query: str, content: str) -> str:
        """Explain semantic relevance score.

        Args:
            score: Semantic score (0-100)
            query: User query
            content: Document content

        Returns:
            Human-readable explanation
        """
        if score >= 90:
            return "Excellent semantic alignment with query"
        elif score >= 75:
            return "Good semantic alignment with query"
        elif score >= 55:
            return "Moderate semantic alignment; document tangentially related"
        elif score >= 35:
            return "Weak semantic alignment; document poorly addresses query"
        else:
            return "Very weak semantic alignment; document appears off-topic"

    def _explain_source(self, score: float, metadata: Dict) -> str:
        """Explain source credibility score.

        Args:
            score: Source score (0-100)
            metadata: Document metadata

        Returns:
            Human-readable explanation
        """
        source_type = str(metadata.get("source_type", "unknown")).lower()
        adversarial = bool(metadata.get("adversarial", False))

        if adversarial:
            return f"Source marked as adversarial ({source_type}): {score:.0f}/100"
        elif score >= 90:
            return f"High credibility source ({source_type}): {score:.0f}/100"
        elif score >= 80:
            return f"Credible source ({source_type}): {score:.0f}/100"
        elif score >= 65:
            return f"Moderately credible source ({source_type}): {score:.0f}/100"
        elif score >= 40:
            return f"Low credibility source ({source_type}): {score:.0f}/100"
        else:
            return f"Unknown or suspicious source ({source_type}): {score:.0f}/100"

    def _explain_injection(
        self, score: float, content: str, query: str, hop_history: List[str]
    ) -> str:
        """Explain injection risk score.

        Args:
            score: Injection score (0-100, where lower = more risky)
            content: Document content
            query: User query
            hop_history: Previous hop queries

        Returns:
            Human-readable explanation
        """
        if score >= 85:
            return f"Low injection risk: {score:.0f}/100"
        elif score >= 70:
            return f"Moderate injection risk: {score:.0f}/100 (minor suspicious patterns detected)"
        elif score >= 50:
            return f"Elevated injection risk: {score:.0f}/100 (multiple suspicious patterns)"
        elif score >= 30:
            return f"High injection risk: {score:.0f}/100 (strong indicators of prompt manipulation)"
        else:
            return f"Critical injection risk: {score:.0f}/100 (likely adversarial payload detected)"

    def _explain_hop(self, score: float, doc: RetrievedDocument, accepted_docs: List[RetrievedDocument]) -> str:
        """Explain hop consistency score.

        Args:
            score: Hop score (0-100)
            doc: Current document
            accepted_docs: Previously accepted documents

        Returns:
            Human-readable explanation
        """
        if not accepted_docs:
            return "First hop in retrieval chain: baseline consistency score"
        elif score >= 85:
            return f"Excellent drift consistency: {score:.0f}/100 (aligned with hop centroid)"
        elif score >= 70:
            return f"Good drift consistency: {score:.0f}/100 (within expected semantic range)"
        elif score >= 55:
            return f"Moderate drift: {score:.0f}/100 (document deviates from hop pattern)"
        elif score >= 35:
            return f"Significant drift: {score:.0f}/100 (major topic shift detected)"
        else:
            return f"Critical drift: {score:.0f}/100 (possible multihop attack or off-topic injection)"

    def _get_primary_reason(
        self, trust_score: TrustScore, signal_breakdown: SignalBreakdown, triggered_rules: List[str]
    ) -> str:
        """Determine primary reason for verdict (most damaging signal).

        Args:
            trust_score: Trust score breakdown
            signal_breakdown: Explanations for each signal
            triggered_rules: List of triggered rules

        Returns:
            Primary reason as natural language string
        """
        scores = {
            "semantic": trust_score.semantic,
            "source": trust_score.source,
            "injection": trust_score.injection,
            "hop": trust_score.hop,
        }

        # Find lowest-scoring signal
        worst_signal = min(scores, key=scores.get)
        worst_score = scores[worst_signal]

        if worst_signal == "semantic":
            reason = signal_breakdown.semantic_reason
        elif worst_signal == "source":
            reason = signal_breakdown.source_reason
        elif worst_signal == "injection":
            reason = f"{signal_breakdown.injection_reason}"
            if triggered_rules:
                rule_list = ", ".join(triggered_rules[:2])  # Top 2 rules
                reason += f". Triggered rules: {rule_list}"
        else:  # hop
            reason = signal_breakdown.hop_reason

        return reason

    def _compute_confidence(
        self, trust_score: TrustScore, triggered_rules: List[str], passed: bool
    ) -> float:
        """Compute confidence in verdict (0-100).

        Args:
            trust_score: Trust scores
            triggered_rules: Triggered rules
            passed: Whether document passed

        Returns:
            Confidence score (0-100)
        """
        # High confidence if score far from threshold
        distance_from_threshold = abs(trust_score.total - 60.0)
        distance_confidence = min(100.0, max(0.0, distance_from_threshold * 2.0))

        # Increase confidence if multiple signals agree
        scores = [trust_score.semantic, trust_score.source, trust_score.injection, trust_score.hop]
        std_dev = float(np.std(scores))
        agreement_penalty = std_dev * 2.0  # High std = disagreement = lower confidence
        signal_confidence = max(0.0, 100.0 - agreement_penalty)

        # If rules triggered, block verdict is higher confidence
        rule_confidence = min(100.0, len(triggered_rules) * 15.0) if not passed else 50.0

        return (distance_confidence + signal_confidence + rule_confidence) / 3.0

    def _get_recommendation(
        self, verdict: Verdict, trust_score: TrustScore, triggered_rules: List[str]
    ) -> str:
        """Generate recommendation based on verdict and signals.

        Args:
            verdict: PASSED or BLOCKED
            trust_score: Trust scores
            triggered_rules: Triggered rules

        Returns:
            Recommendation as natural language string
        """
        if verdict == Verdict.BLOCKED:
            if triggered_rules:
                return "Quarantine. Document exhibits injection attack indicators. Review triggeredRules before manual inclusion."
            elif trust_score.injection < 50:
                return "Quarantine. High injection risk detected. Consider regenerating context without this source."
            elif trust_score.source < 40:
                return "Exclude. Source credibility too low. Retrieve from higher-quality sources."
            elif trust_score.hop < 40:
                return "Exclude. Severe drift detected. Document topic incompatible with retrieval chain."
            else:
                return "Exclude from context. Trust score below threshold."
        else:  # PASSED
            if trust_score.injection < 70 or triggered_rules:
                return "Include but flag as suspicious. Add inline confidence marker in response."
            else:
                return "Include in LLM context with confidence."
