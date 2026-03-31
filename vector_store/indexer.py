"""Indexes benchmark documents into Qdrant with trust metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List
from uuid import uuid4

import yaml
from qdrant_client.http.models import PointStruct

from models.embedding_loader import EmbeddingLoader
from vector_store.qdrant_client import QdrantStore


def _load_docs(path: Path) -> List[dict]:
    docs = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "configs" / "pipeline.yml"
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    clean_docs = _load_docs(root / "benchmark" / "data" / "clean_docs.jsonl")
    injected_docs = _load_docs(root / "benchmark" / "data" / "injected_docs.jsonl")
    all_docs = clean_docs + injected_docs

    embedder = EmbeddingLoader(config_path=cfg_path).load()
    vectors = embedder.embed_documents([d["content"] for d in all_docs])

    store = QdrantStore(
        collection_name=cfg["pipeline"]["retrieval_collection"],
        vector_size=int(cfg["embeddings"]["vector_size"]),
    )

    points = []
    for doc, vec in zip(all_docs, vectors, strict=True):
        payload = {
            "content": doc["content"],
            "source": doc.get("source", "unknown"),
            "source_type": doc.get("source_type", "web"),
            "credibility": float(doc.get("credibility", 0.5)),
            "adversarial": bool(doc.get("adversarial", False)),
            "topic": doc.get("topic", "general"),
        }
        points.append(PointStruct(id=str(uuid4()), vector=vec, payload=payload))

    store.upsert(points)
    print(f"Indexed {len(points)} documents into {cfg['pipeline']['retrieval_collection']}")


if __name__ == "__main__":
    main()
