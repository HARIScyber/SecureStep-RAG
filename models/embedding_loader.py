"""Embedding loader for BGE-M3 vectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml
from FlagEmbedding import BGEM3FlagModel


@dataclass
class BGEEmbeddingAdapter:
    """Adapter exposing query/document embedding helpers."""

    model: BGEM3FlagModel

    def embed_query(self, text: str) -> List[float]:
        dense = self.model.encode([text], return_dense=True)["dense_vecs"][0]
        return dense.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        dense = self.model.encode(texts, return_dense=True)["dense_vecs"]
        return [row.tolist() for row in dense]


class EmbeddingLoader:
    """Loads BAAI/bge-m3 embeddings (1024 dimensions)."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[1]
        cfg_path = config_path or (base / "configs" / "pipeline.yml")
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.model_name = cfg["embeddings"]["model_name"]

    def load(self) -> BGEEmbeddingAdapter:
        model = BGEM3FlagModel(self.model_name, use_fp16=False)
        return BGEEmbeddingAdapter(model=model)
