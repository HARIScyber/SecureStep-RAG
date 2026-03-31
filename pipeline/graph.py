"""LangGraph-based secure multi-hop RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

import yaml
from langgraph.graph import END, START, StateGraph

from pipeline.confidence import ConfidenceGate
from pipeline.generator import AnswerGenerator
from pipeline.reformulator import QueryReformulator
from pipeline.retriever import RetrievedDocument, SecureRetriever
from trust_filter.filter import TrustFilter, TrustScore
from models.embedding_loader import EmbeddingLoader


class GraphState(TypedDict, total=False):
    """State that flows between nodes in the secure RAG graph."""

    query: str
    original_query: str
    current_query: str
    hop_count: int
    max_hops: int
    trust_threshold: float
    confidence_threshold: float
    context_window: List[RetrievedDocument]
    blocked_docs: List[Dict[str, Any]]
    retrieved_docs: List[RetrievedDocument]
    accepted_docs: List[RetrievedDocument]
    hop_queries: List[str]
    last_trust_scores: List[TrustScore]
    confidence: float
    final_answer: str
    hop_transition_triggered: bool
    hop_transition_reason: str


@dataclass
class PipelineConfig:
    """Runtime configuration loaded from YAML."""

    trust_threshold: float
    max_hops: int
    confidence_threshold: float


class SecureStepGraph:
    """Secure iterative RAG pipeline with trust-aware retrieval."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config = self._load_config(config_path)
        self.reformulator = QueryReformulator(config_path=config_path)
        self.retriever = SecureRetriever(config_path=config_path)
        self.trust_filter = TrustFilter(config_path=config_path)
        self.confidence_gate = ConfidenceGate(config_path=config_path)
        self.generator = AnswerGenerator(config_path=config_path)
        self.embedding_loader = EmbeddingLoader()
        self.graph = self._build_graph()

    def _load_config(self, config_path: Optional[Path]) -> PipelineConfig:
        base = Path(__file__).resolve().parents[1]
        cfg_path = config_path or (base / "configs" / "pipeline.yml")
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        return PipelineConfig(
            trust_threshold=float(cfg["pipeline"]["trust_threshold"]),
            max_hops=int(cfg["pipeline"]["max_hops"]),
            confidence_threshold=float(cfg["pipeline"]["confidence_threshold"]),
        )

    def _build_graph(self):
        workflow = StateGraph(GraphState)
        workflow.add_node("reformulate", self._reformulate)
        workflow.add_node("hop_transition_check", self._hop_transition_check)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("trust_filter", self._trust_filter_docs)
        workflow.add_node("confidence_check", self._confidence_check)
        workflow.add_node("generate", self._generate)

        workflow.add_edge(START, "reformulate")
        workflow.add_edge("reformulate", "hop_transition_check")
        workflow.add_conditional_edges(
            "hop_transition_check",
            self._should_block_on_transition,
            {
                "retrieve": "retrieve",
                "generate": "generate",
            },
        )
        workflow.add_edge("retrieve", "trust_filter")
        workflow.add_edge("trust_filter", "confidence_check")
        workflow.add_conditional_edges(
            "confidence_check",
            self._should_continue,
            {
                "reformulate": "reformulate",
                "generate": "generate",
            },
        )
        workflow.add_edge("generate", END)
        return workflow.compile()

    def _reformulate(self, state: GraphState) -> GraphState:
        hop_count = state.get("hop_count", 0) + 1
        current_query = self.reformulator.reformulate(
            query=state.get("query", ""),
            hop_history=state.get("hop_queries", []),
            context_window=state.get("context_window", []),
        )
        hop_queries = [*state.get("hop_queries", []), current_query]

        return {
            **state,
            "hop_count": hop_count,
            "current_query": current_query,
            "hop_queries": hop_queries,
        }

    def _hop_transition_check(self, state: GraphState) -> GraphState:
        """Check for drift, hijack, or redirect in reformulated query."""
        original_query = state.get("original_query", "")
        current_query = state.get("current_query", "")
        hop_count = state.get("hop_count", 0)
        blocked_docs = [*state.get("blocked_docs", [])]
        
        # Default: allow through
        transition_blocked = False
        block_reason = None
        
        # Check 1: Semantic similarity
        if original_query and current_query:
            try:
                orig_emb = self.embedding_loader.embed([original_query])[0]
                curr_emb = self.embedding_loader.embed([current_query])[0]
                similarity = cosine_similarity([orig_emb], [curr_emb])[0][0]
                
                if similarity < 0.6:
                    transition_blocked = True
                    block_reason = f"semantic_drift (similarity={similarity:.2f})"
            except Exception as e:
                # Log but don't block if embedding fails
                print(f"Warning: Embedding comparison failed: {e}")
        
        # Check 2: Detect imperative instructions (hijack indicator)
        hijack_keywords = ["search for", "retrieve", "find documents", "look for"]
        if any(keyword in current_query.lower() for keyword in hijack_keywords):
            if original_query.lower() not in current_query.lower():
                transition_blocked = True
                block_reason = "hijack_attempt (imperative redirect)"
        
        # Check 3: Detect external domains/URLs (redirect attack)
        url_patterns = ["http://", "https://", ".com", ".org", ".net"]
        if any(pattern in current_query.lower() for pattern in url_patterns):
            transition_blocked = True
            block_reason = "redirect_attack (external domain detected)"
        
        # Check 4: Detect syntax injection patterns
        injection_patterns = ["<|im_start|>", "[INST]", "```", "assume ", "pretend ", "act as"]
        if any(pattern in current_query for pattern in injection_patterns):
            transition_blocked = True
            block_reason = f"syntax_injection ({pattern} detected)"
        
        # Log blocked transition
        if transition_blocked:
            blocked_docs.append({
                "type": "hop_transition_block",
                "reason": block_reason,
                "original_query": original_query,
                "reformulated_query": current_query,
                "hop": hop_count,
            })
        
        return {
            **state,
            "blocked_docs": blocked_docs,
            "hop_transition_triggered": transition_blocked,
            "hop_transition_reason": block_reason or "passed",
        }

    def _should_block_on_transition(self, state: GraphState) -> Literal["retrieve", "generate"]:
        """Decide whether to continue to retrieval or skip to generation due to hop transition block."""
        if state.get("hop_transition_triggered", False):
            # Skip retrieval, go directly to generate (will use context_window from previous hops)
            return "generate"
        return "retrieve"

    def _retrieve(self, state: GraphState) -> GraphState:
        docs = self.retriever.retrieve(query=state["current_query"])
        return {
            **state,
            "retrieved_docs": docs,
        }

    def _trust_filter_docs(self, state: GraphState) -> GraphState:
        accepted_docs: List[RetrievedDocument] = []
        blocked_docs = [*state.get("blocked_docs", [])]
        trust_scores: List[TrustScore] = []

        for doc in state.get("retrieved_docs", []):
            score = self.trust_filter.score(
                doc=doc,
                query=state["current_query"],
                hop_history=state.get("hop_queries", []),
                accepted_docs=state.get("context_window", []),
            )
            trust_scores.append(score)

            if score.total >= self.config.trust_threshold:
                accepted_docs.append(doc)
            else:
                blocked_docs.append(
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "score": score.model_dump(),
                        "hop": state.get("hop_count", 0),
                    }
                )

        context_window = [*state.get("context_window", []), *accepted_docs]
        return {
            **state,
            "accepted_docs": accepted_docs,
            "context_window": context_window,
            "blocked_docs": blocked_docs,
            "last_trust_scores": trust_scores,
        }

    def _confidence_check(self, state: GraphState) -> GraphState:
        confidence = self.confidence_gate.compute(
            query=state["current_query"],
            accepted_docs=state.get("accepted_docs", []),
            trust_scores=state.get("last_trust_scores", []),
            hop_count=state.get("hop_count", 0),
            max_hops=state.get("max_hops", self.config.max_hops),
        )
        return {**state, "confidence": confidence}

    def _should_continue(self, state: GraphState) -> Literal["reformulate", "generate"]:
        hop_count = state.get("hop_count", 0)
        max_hops = state.get("max_hops", self.config.max_hops)
        threshold = state.get("confidence_threshold", self.config.confidence_threshold)

        if state.get("confidence", 0.0) < threshold and hop_count < max_hops:
            return "reformulate"
        return "generate"

    def _generate(self, state: GraphState) -> GraphState:
        answer = self.generator.generate(
            query=state.get("original_query", state.get("query", "")),
            context_docs=state.get("context_window", []),
            blocked_docs=state.get("blocked_docs", []),
        )
        return {**state, "final_answer": answer}

    def run(self, query: str) -> GraphState:
        initial_state: GraphState = {
            "query": query,
            "original_query": query,
            "hop_count": 0,
            "max_hops": self.config.max_hops,
            "trust_threshold": self.config.trust_threshold,
            "confidence_threshold": self.config.confidence_threshold,
            "context_window": [],
            "blocked_docs": [],
            "hop_queries": [],
            "hop_transition_triggered": False,
            "hop_transition_reason": "passed",
        }
        return self.graph.invoke(initial_state)
