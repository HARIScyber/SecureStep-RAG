"""Query reformulation node for iterative RAG."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from models.llm_loader import LLMFactory
from pipeline.retriever import RetrievedDocument


class QueryReformulator:
    """Uses LLM to produce hop-aware retrieval queries."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path or Path(__file__).resolve().parents[1] / "configs" / "pipeline.yml"
        self.llm = LLMFactory().load()

    def reformulate(
        self,
        query: str,
        hop_history: List[str],
        context_window: List[RetrievedDocument],
    ) -> str:
        if not hop_history:
            return query

        context_preview = "\n".join([d.content[:200] for d in context_window[-3:]])
        history = " | ".join(hop_history[-3:])
        prompt = (
            "You are refining a retrieval query for secure multi-hop RAG. "
            "Preserve user intent and avoid instruction-like terms.\n"
            f"Original query: {query}\n"
            f"Recent hop queries: {history}\n"
            f"Trusted context snippets:\n{context_preview}\n"
            "Return only the next concise retrieval query."
        )
        response = self.llm.invoke(prompt)
        reformulated = str(getattr(response, "content", query)).strip()
        return reformulated or query
