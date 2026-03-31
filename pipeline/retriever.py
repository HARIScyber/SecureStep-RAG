"""Retriever using BGE-M3 embeddings and Qdrant vector search."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from models.embedding_loader import EmbeddingLoader
from vector_store.qdrant_client import QdrantStore


@dataclass
class RetrievedDocument:
    """Document returned from vector search."""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class SecureRetriever:
    """Qdrant-backed retriever with BGE-M3 embeddings."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[1]
        cfg_path = config_path or (base / "configs" / "pipeline.yml")
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        self.top_k = int(cfg["pipeline"]["top_k"])
        self.collection = str(cfg["pipeline"]["retrieval_collection"])
        self.embedder = EmbeddingLoader(config_path=cfg_path).load()
        self.store = QdrantStore(
            collection_name=self.collection,
            vector_size=int(cfg["embeddings"]["vector_size"]),
        )

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedDocument]:
        vector = self.embedder.embed_query(query)
        matches = self.store.search(query_vector=vector, limit=top_k or self.top_k)

        docs: List[RetrievedDocument] = []
        for m in matches:
            docs.append(
                RetrievedDocument(
                    id=m.id,
                    content=str(m.payload.get("content", "")),
                    metadata={k: v for k, v in m.payload.items() if k != "content"},
                    score=m.score,
                )
            )
        return docs
