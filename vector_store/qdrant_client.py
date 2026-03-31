"""Qdrant wrapper with trust-aware payload conventions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams


@dataclass
class QdrantMatch:
    """Search result container."""

    id: str
    score: float
    payload: Dict[str, Any]


class QdrantStore:
    """Thin wrapper around QdrantClient for secure RAG flows."""

    def __init__(self, collection_name: str, vector_size: int = 1024) -> None:
        load_dotenv()
        self.collection_name = collection_name
        self.vector_size = vector_size
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.client = QdrantClient(url=url)
        self.ensure_collection()

    def ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def upsert(self, points: List[PointStruct]) -> None:
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        query_vector: List[float],
        limit: int,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[QdrantMatch]:
        q_filter = None
        if metadata_filter:
            q_filter = Filter(
                must=[
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in metadata_filter.items()
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=q_filter,
            limit=limit,
            with_payload=True,
        )
        return [
            QdrantMatch(
                id=str(item.id),
                score=float(item.score),
                payload=item.payload or {},
            )
            for item in results
        ]
