"""FastAPI entrypoint for SecureStep-RAG."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from pipeline.graph import SecureStepGraph

app = FastAPI(title="SecureStep-RAG", version="0.1.0")
pipeline = SecureStepGraph()


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest) -> dict:
    result = pipeline.run(req.query)
    return {
        "answer": result.get("final_answer", ""),
        "hop_count": result.get("hop_count", 0),
        "blocked_docs": len(result.get("blocked_docs", [])),
        "hop_queries": result.get("hop_queries", []),
    }
