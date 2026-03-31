"""Final answer generator using trusted context only."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.llm_loader import LLMFactory
from pipeline.retriever import RetrievedDocument


class AnswerGenerator:
    """Builds final grounded answer from safe context window."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        del config_path
        self.llm = LLMFactory().load()

    def generate(
        self,
        query: str,
        context_docs: List[RetrievedDocument],
        blocked_docs: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        safe_context = "\n\n".join(
            [f"[doc:{d.id}] {d.content[:900]}" for d in context_docs[:10]]
        )
        blocked_count = len(blocked_docs or [])

        prompt = (
            "Answer the user query using only trusted context. "
            "If context is insufficient, explicitly say so.\n"
            f"Query: {query}\n"
            f"Blocked docs count: {blocked_count}\n"
            f"Trusted context:\n{safe_context}\n"
            "Return a concise, factual response with key supporting points."
        )
        response = self.llm.invoke(prompt)
        return str(getattr(response, "content", "No answer generated.")).strip()
