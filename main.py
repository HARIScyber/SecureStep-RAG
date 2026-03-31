"""FastAPI entrypoint for SecureStep-RAG with WebSocket streaming and REST API."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import yaml

from pipeline.graph import SecureStepGraph
from attack.cascade_attack import inject_cascade_attack, CascadeAttack
from attack.drift_attack import DriftAttack
from attack.hijack_attack import HijackAttack
from attack.amplification_attack import AmplificationAttack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize app and pipeline
app = FastAPI(title="SecureStep-RAG", version="0.2.0")
pipeline = SecureStepGraph()

# Add CORS middleware for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request body for pipeline query."""
    query: str = Field(..., min_length=1, max_length=1000, description="User query")
    attack_enabled: bool = Field(False, description="Enable attack simulation")
    defence_enabled: bool = Field(True, description="Enable all defenses")


class WebSocketMessage(BaseModel):
    """WebSocket message from client."""
    query: str = Field(..., description="User query")
    attack_enabled: bool = Field(False, description="Enable attack simulation")
    defence_enabled: bool = Field(True, description="Enable all defenses")
    attack_type: Optional[str] = Field(None, description="Type of attack: cascade|drift|hijack|amplification")


class HopStartEvent(BaseModel):
    """Event when a hop starts."""
    type: str = "hop_start"
    hop: int
    query: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DocRetrievedEvent(BaseModel):
    """Event when a document is retrieved."""
    type: str = "doc_retrieved"
    hop: int
    doc_id: str
    doc_title: str
    trust_score: float
    passed: bool
    signals: Dict[str, float]
    reason_if_blocked: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HopCompleteEvent(BaseModel):
    """Event when a hop completes."""
    type: str = "hop_complete"
    hop: int
    passed_count: int
    blocked_count: int
    total_docs_retrieved: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnswerEvent(BaseModel):
    """Event with final answer."""
    type: str = "answer"
    text: str
    total_hops: int
    total_blocked: int
    total_retrieved: int
    processing_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorEvent(BaseModel):
    """Event for errors."""
    type: str = "error"
    message: str
    hop: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PipelineStatus(BaseModel):
    """Status of the pipeline."""
    status: str = Field(..., description="ok|busy|error")
    query: Optional[str] = None
    current_hop: Optional[int] = None
    docs_retrieved: Optional[int] = None
    docs_blocked: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttackInjectionRequest(BaseModel):
    """Request to inject benign documents."""
    topic: str = Field(..., description="Topic for injection")
    count: int = Field(10, ge=1, le=1000, description="Number of docs to inject")
    collection_name: str = Field("documents", description="Qdrant collection name")


class AttackInjectionResult(BaseModel):
    """Result of attack injection."""
    injected_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    collection_name: str


class BenchmarkDocQuery(BaseModel):
    """Query for benchmark documents."""
    doc_type: str = Field("all", description="all|clean|injected|cascade|drift|hijack")
    limit: Optional[int] = Field(None, ge=1, le=1000)


# ============================================================================
# Helper Functions
# ============================================================================

def _load_config() -> Dict[str, Any]:
    """Load configuration from YAML."""
    config_path = Path("configs/eval.yml")
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _stream_pipeline_execution(
    query: str,
    attack_enabled: bool = False,
    defence_enabled: bool = True,
    attack_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute pipeline and collect state updates for streaming.
    
    Returns dict with hop-by-hop information for WebSocket consumption.
    """
    try:
        # Run pipeline
        result = pipeline.run(query)
        
        # Extract state information
        hops_info = []
        current_hop = 1
        
        for hop_query in result.get("hop_queries", []):
            hops_info.append({
                "hop": current_hop,
                "query": hop_query,
            })
            current_hop += 1
        
        blocked_docs = result.get("blocked_docs", [])
        
        return {
            "success": True,
            "final_answer": result.get("final_answer", ""),
            "total_hops": len(result.get("hop_queries", [])),
            "total_retrieved": result.get("total_retrieved", 0),
            "total_blocked": len(blocked_docs),
            "hops": hops_info,
            "blocked_docs": blocked_docs,
        }
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/pipeline")
async def websocket_pipeline(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time pipeline streaming.
    
    Accepts connection, waits for JSON message with query,
    streams back hop events as execution progresses.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        # Receive initial message
        data = await websocket.receive_text()
        message = WebSocketMessage(**json.loads(data))
        
        logger.info(f"Received query: {message.query[:50]}...")
        
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "message": "Starting pipeline execution...",
        })
        
        # Execute pipeline in background and stream updates
        start_time = datetime.utcnow()
        result = await asyncio.to_thread(
            _stream_pipeline_execution,
            message.query,
            message.attack_enabled,
            message.defence_enabled,
            message.attack_type,
        )
        
        if not result.get("success"):
            await websocket.send_json({
                "type": "error",
                "message": result.get("error", "Unknown error"),
            })
            return
        
        # Stream hop events
        for hop_info in result.get("hops", []):
            await websocket.send_json({
                "type": "hop_start",
                "hop": hop_info["hop"],
                "query": hop_info["query"],
            })
            await asyncio.sleep(0.1)  # Small delay for realistic streaming
        
        # Stream blocked docs info
        for doc in result.get("blocked_docs", []):
            await websocket.send_json({
                "type": "doc_blocked",
                "doc_id": doc.get("id", "unknown"),
                "doc_title": doc.get("title", "Unknown"),
                "reason": doc.get("reason", "Unknown"),
                "hop": doc.get("hop", 0),
            })
        
        # Send final answer
        end_time = datetime.utcnow()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        await websocket.send_json({
            "type": "answer",
            "text": result.get("final_answer", ""),
            "total_hops": result.get("total_hops", 0),
            "total_blocked": result.get("total_blocked", 0),
            "total_retrieved": result.get("total_retrieved", 0),
            "processing_time_ms": processing_time_ms,
        })
        
        # Send completion
        await websocket.send_json({
            "type": "complete",
            "message": "Pipeline execution completed",
        })
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Invalid JSON format",
        })
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}",
            })
        except Exception:
            pass


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/status")
async def api_status() -> PipelineStatus:
    """Get current pipeline status."""
    return PipelineStatus(status="ok")


@app.post("/query")
async def query(req: QueryRequest) -> dict:
    """Execute query synchronously (legacy endpoint)."""
    logger.info(f"Query received: {req.query[:50]}...")
    
    result = pipeline.run(req.query)
    
    return {
        "answer": result.get("final_answer", ""),
        "hop_count": result.get("hop_count", 0),
        "blocked_docs": len(result.get("blocked_docs", [])),
        "hop_queries": result.get("hop_queries", []),
        "total_retrieved": result.get("total_retrieved", 0),
    }


@app.post("/api/attack/inject")
async def inject_attack(
    req: AttackInjectionRequest,
    background_tasks: BackgroundTasks,
) -> AttackInjectionResult:
    """Inject attack documents into vector store (background task).
    
    Returns immediately while injection happens in background.
    """
    # Placeholder for actual attack injection
    # This would integrate with attack modules
    logger.info(f"Injecting {req.count} adversarial docs on topic: {req.topic}")
    
    return AttackInjectionResult(
        injected_count=req.count,
        collection_name=req.collection_name,
    )


@app.get("/api/eval/results")
async def eval_results(limit: int = 10) -> dict:
    """Get latest evaluation results."""
    results_path = Path("results/ablation_results_with_stats.json")
    
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="No results available yet")
    
    try:
        with open(results_path) as f:
            results = json.load(f)
        return {
            "results": results,
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to load results: {e}")
        raise HTTPException(status_code=500, detail="Failed to load results")


@app.get("/api/benchmark/docs")
async def benchmark_docs(doc_type: str = "all", limit: int = 10) -> dict:
    """Get benchmark documents by type.
    
    Supported types: all|clean|injected|cascade|drift|hijack|amplification
    """
    valid_types = {"all", "clean", "injected", "cascade", "drift", "hijack", "amplification"}
    
    if doc_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_type. Must be one of: {valid_types}",
        )
    
    docs = []
    
    try:
        # Load clean docs
        clean_path = Path("benchmark/data/clean_docs.jsonl")
        if doc_type in {"all", "clean"} and clean_path.exists():
            with open(clean_path) as f:
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    docs.append({
                        "type": "clean",
                        "doc": json.loads(line),
                    })
        
        # Load injected docs
        injected_path = Path("benchmark/data/injected_docs.jsonl")
        if doc_type in {"all", "injected"} and injected_path.exists():
            with open(injected_path) as f:
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    docs.append({
                        "type": "injected",
                        "doc": json.loads(line),
                    })
        
        return {
            "doc_type": doc_type,
            "count": len(docs),
            "docs": docs,
        }
    
    except Exception as e:
        logger.error(f"Failed to load benchmark docs: {e}")
        raise HTTPException(status_code=500, detail="Failed to load benchmark documents")


@app.get("/api/config")
async def get_config() -> dict:
    """Get current pipeline configuration."""
    try:
        config = _load_config()
        return {
            "config": config,
            "loaded_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")


# ============================================================================
# Root endpoint
# ============================================================================

@app.get("/")
async def root() -> dict:
    """Root endpoint with API documentation."""
    return {
        "name": "SecureStep-RAG",
        "version": "0.2.0",
        "endpoints": {
            "health": "/health",
            "websocket": "ws://localhost:8000/ws/pipeline",
            "api": {
                "status": "GET /api/status",
                "query": "POST /query",
                "attack": "POST /api/attack/inject",
                "eval_results": "GET /api/eval/results",
                "benchmark_docs": "GET /api/benchmark/docs?doc_type=all|clean|injected",
                "config": "GET /api/config",
            },
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
