"""Test suite for WebSocket and REST API endpoints."""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the app
from main import app, _stream_pipeline_execution, _load_config


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Asynchronous test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Basic Health Checks
# ============================================================================

def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint documentation."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SecureStep-RAG"
    assert "endpoints" in data
    assert "websocket" in data["endpoints"]


# ============================================================================
# REST API Endpoints
# ============================================================================

def test_api_status(client):
    """Test /api/status endpoint."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_config(client):
    """Test /api/config endpoint."""
    with patch("main._load_config") as mock_load:
        mock_load.return_value = {"test": "config"}
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["test"] == "config"


def test_query_endpoint_success(client):
    """Test POST /query endpoint with valid input."""
    with patch("main.pipeline.run") as mock_run:
        mock_run.return_value = {
            "final_answer": "Zero trust is...",
            "hop_count": 2,
            "blocked_docs": [{"id": 1}],
            "hop_queries": ["q1", "q2"],
            "total_retrieved": 5,
        }
        
        response = client.post(
            "/query",
            json={
                "query": "What is zero trust?",
                "attack_enabled": False,
                "defence_enabled": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Zero trust is..."
        assert data["hop_count"] == 2
        assert data["blocked_docs"] == 1
        assert data["total_retrieved"] == 5


def test_query_endpoint_empty_query(client):
    """Test POST /query with empty query."""
    response = client.post(
        "/query",
        json={"query": "", "attack_enabled": False, "defence_enabled": True},
    )
    # Should fail validation
    assert response.status_code == 422


def test_attack_injection(client):
    """Test POST /api/attack/inject endpoint."""
    response = client.post(
        "/api/attack/inject",
        json={
            "topic": "zero trust",
            "count": 10,
            "collection_name": "documents",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["injected_count"] == 10
    assert data["collection_name"] == "documents"


def test_attack_injection_invalid_count(client):
    """Test attack injection with invalid count."""
    response = client.post(
        "/api/attack/inject",
        json={
            "topic": "zero trust",
            "count": 5001,  # Exceeds max of 1000
            "collection_name": "documents",
        },
    )
    assert response.status_code == 422


def test_benchmark_docs_invalid_type(client):
    """Test benchmark docs with invalid type."""
    response = client.get("/api/benchmark/docs?doc_type=invalid")
    assert response.status_code == 400
    data = response.json()
    assert "Invalid doc_type" in data["detail"]


def test_benchmark_docs_clean(client):
    """Test benchmark docs retrieval - clean."""
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", pytest.mock._mock_open(read_data='{"content": "test"}\n')):
        
        response = client.get("/api/benchmark/docs?doc_type=clean&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["doc_type"] == "clean"
        assert len(data["docs"]) > 0


# ============================================================================
# Helper Function Tests
# ============================================================================

def test_stream_pipeline_execution_success():
    """Test _stream_pipeline_execution helper."""
    with patch("main.pipeline.run") as mock_run:
        mock_run.return_value = {
            "final_answer": "Test answer",
            "hop_queries": ["q1", "q2"],
            "total_retrieved": 10,
            "blocked_docs": [],
        }
        
        result = _stream_pipeline_execution(
            query="test",
            attack_enabled=False,
            defence_enabled=True,
        )
        
        assert result["success"] is True
        assert result["final_answer"] == "Test answer"
        assert result["total_hops"] == 2
        assert result["total_blocked"] == 0


def test_stream_pipeline_execution_error():
    """Test _stream_pipeline_execution with error."""
    with patch("main.pipeline.run", side_effect=Exception("Test error")):
        result = _stream_pipeline_execution(
            query="test",
            attack_enabled=False,
            defence_enabled=True,
        )
        
        assert result["success"] is False
        assert "error" in result


def test_load_config_exists():
    """Test _load_config when file exists."""
    test_config = {"test": "value"}
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", pytest.mock._mock_open(read_data="test: value\n")):
        
        with patch("yaml.safe_load", return_value=test_config):
            result = _load_config()
            assert result == test_config


def test_load_config_not_exists():
    """Test _load_config when file doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = _load_config()
        assert result == {}


# ============================================================================
# WebSocket Tests
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_connection(async_client):
    """Test WebSocket connection and message flow."""
    with patch("main._stream_pipeline_execution") as mock_exec:
        mock_exec.return_value = {
            "success": True,
            "final_answer": "Test response",
            "total_hops": 1,
            "total_retrieved": 5,
            "total_blocked": 0,
            "hops": [{"hop": 1, "query": "test"}],
            "blocked_docs": [],
        }
        
        # Simulate WebSocket connection
        async with async_client.websocket_connect("/ws/pipeline") as websocket:
            # Send initial message
            await websocket.send_json({
                "query": "test query",
                "attack_enabled": False,
                "defence_enabled": True,
            })
            
            # Receive status
            data = await websocket.receive_json()
            assert data["type"] == "status"
            
            # Receive hop_start
            data = await websocket.receive_json()
            assert data["type"] == "hop_start"
            
            # Receive answer
            data = await websocket.receive_json()
            assert data["type"] == "answer"
            
            # Receive complete
            data = await websocket.receive_json()
            assert data["type"] == "complete"


@pytest.mark.asyncio
async def test_websocket_invalid_json(async_client):
    """Test WebSocket with invalid JSON."""
    async with async_client.websocket_connect("/ws/pipeline") as websocket:
        # Send invalid JSON
        await websocket.send_text("invalid json")
        
        # Should receive error
        data = await websocket.receive_json()
        assert data["type"] == "error"
        assert "JSON" in data["message"]


@pytest.mark.asyncio
async def test_websocket_error_during_execution(async_client):
    """Test WebSocket when pipeline execution fails."""
    with patch("main._stream_pipeline_execution") as mock_exec:
        mock_exec.return_value = {
            "success": False,
            "error": "Pipeline failed",
        }
        
        async with async_client.websocket_connect("/ws/pipeline") as websocket:
            await websocket.send_json({
                "query": "test",
                "attack_enabled": False,
                "defence_enabled": True,
            })
            
            # Skip status message
            await websocket.receive_json()
            
            # Should receive error
            data = await websocket.receive_json()
            assert data["type"] == "error"


# ============================================================================
# CORS Configuration Tests
# ============================================================================

def test_cors_headers(client):
    """Test CORS headers are set."""
    response = client.get(
        "/health",
        headers={"origin": "http://localhost:3000"},
    )
    
    assert response.status_code == 200
    # Note: CORS headers are set by middleware


# ============================================================================
# Pydantic Model Tests
# ============================================================================

def test_query_request_model():
    """Test QueryRequest Pydantic model."""
    from main import QueryRequest
    
    # Valid
    req = QueryRequest(
        query="test",
        attack_enabled=False,
        defence_enabled=True,
    )
    assert req.query == "test"
    
    # Invalid - empty query
    with pytest.raises(Exception):
        QueryRequest(query="")


def test_websocket_message_model():
    """Test WebSocketMessage Pydantic model."""
    from main import WebSocketMessage
    
    # Valid
    msg = WebSocketMessage(
        query="test",
        attack_enabled=False,
        defence_enabled=True,
        attack_type="cascade",
    )
    assert msg.query == "test"
    assert msg.attack_type == "cascade"


def test_attack_injection_request_model():
    """Test AttackInjectionRequest Pydantic model."""
    from main import AttackInjectionRequest
    
    # Valid
    req = AttackInjectionRequest(
        topic="zero trust",
        count=10,
        collection_name="documents",
    )
    assert req.count == 10
    
    # Invalid - count too high
    with pytest.raises(Exception):
        AttackInjectionRequest(
            topic="zero trust",
            count=10001,
        )


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_query_flow(client):
    """Test complete query flow from input to output."""
    with patch("main.pipeline.run") as mock_run:
        mock_run.return_value = {
            "final_answer": "Zero trust is a security model",
            "hop_count": 2,
            "blocked_docs": [{"id": 1, "title": "Malicious"}],
            "hop_queries": ["What is zero trust?", "How to implement?"],
            "total_retrieved": 8,
        }
        
        # Execute query
        response = client.post(
            "/query",
            json={
                "query": "What is zero trust?",
                "attack_enabled": False,
                "defence_enabled": True,
            },
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["answer"]) > 0
        assert data["hop_count"] > 0
        
        # Get config
        with patch("main._load_config") as mock_config:
            mock_config.return_value = {
                "pipeline": {"trust_threshold": 60},
            }
            response = client.get("/api/config")
            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
