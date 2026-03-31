# SecureStep-RAG WebSocket API Documentation

## Overview

The updated `main.py` provides:
1. **WebSocket streaming** for real-time pipeline execution updates
2. **REST API endpoints** for status, attacks, evaluations, and benchmarks
3. **CORS support** for React dashboard (localhost:3000)
4. **Async/background** task execution
5. **Full type hints** and error handling

## WebSocket Endpoint: `/ws/pipeline`

### Connection & Message Format

**URL**: `ws://localhost:8000/ws/pipeline`

**Initial Message** (Client → Server):
```json
{
  "query": "What is zero trust architecture?",
  "attack_enabled": false,
  "defence_enabled": true,
  "attack_type": null
}
```

**Parameters**:
- `query` (str): User question (required, 1-1000 chars)
- `attack_enabled` (bool): Enable attack simulation (default: false)
- `defence_enabled` (bool): Enable all defenses (default: true)
- `attack_type` (str, optional): One of: `cascade`, `drift`, `hijack`, `amplification`

### Streaming Messages (Server → Client)

#### 1. Status Event
Sent immediately after connection:
```json
{
  "type": "status",
  "message": "Starting pipeline execution..."
}
```

#### 2. Hop Start Events
Sent when each retrieval hop begins:
```json
{
  "type": "hop_start",
  "hop": 1,
  "query": "What is zero trust?"
}
```

#### 3. Document Blocked Events
Sent for each document blocked by trust filter:
```json
{
  "type": "doc_blocked",
  "doc_id": "doc_12345",
  "doc_title": "Malicious Guide",
  "reason": "injection_score=95/100",
  "hop": 1
}
```

#### 4. Final Answer Event
Sent with the LLM response:
```json
{
  "type": "answer",
  "text": "Zero trust is a security model...",
  "total_hops": 3,
  "total_blocked": 2,
  "total_retrieved": 10,
  "processing_time_ms": 1234.56
}
```

#### 5. Completion Event
Sent when pipeline finishes:
```json
{
  "type": "complete",
  "message": "Pipeline execution completed"
}
```

#### 6. Error Event
Sent on any error:
```json
{
  "type": "error",
  "message": "Failed to connect to Qdrant"
}
```

### Example: JavaScript/React Client

```typescript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/ws/pipeline");

ws.onopen = () => {
  // Send initial query
  ws.send(JSON.stringify({
    query: "What is zero trust?",
    attack_enabled: false,
    defence_enabled: true,
    attack_type: null,
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case "status":
      console.log("Status:", message.message);
      break;
    
    case "hop_start":
      console.log(`Hop ${message.hop}: ${message.query}`);
      // Update UI: show hop indicator
      break;
    
    case "doc_blocked":
      console.log(`Blocked: ${message.doc_title}`);
      // Update UI: show blocked document
      break;
    
    case "answer":
      console.log("Answer:", message.text);
      console.log(`Stats: ${message.total_hops} hops, ${message.total_blocked} blocked`);
      // Update UI: display answer + statistics
      break;
    
    case "complete":
      console.log("Done!");
      break;
    
    case "error":
      console.error("Error:", message.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("Connection closed");
};
```

### Example: Python Client

```python
import asyncio
import json
import websockets

async def stream_pipeline():
    uri = "ws://localhost:8000/ws/pipeline"
    
    async with websockets.connect(uri) as websocket:
        # Send query
        await websocket.send(json.dumps({
            "query": "What is zero trust?",
            "attack_enabled": False,
            "defence_enabled": True,
        }))
        
        # Receive streaming updates
        async for message_str in websocket:
            message = json.loads(message_str)
            
            if message["type"] == "hop_start":
                print(f"Hop {message['hop']}: {message['query']}")
            elif message["type"] == "doc_blocked":
                print(f"Blocked: {message['doc_title']} ({message['reason']})")
            elif message["type"] == "answer":
                print(f"Answer: {message['text']}")
                print(f"Statistics: {message}")
            elif message["type"] == "error":
                print(f"Error: {message['message']}")

# Run
asyncio.run(stream_pipeline())
```

## REST API Endpoints

### Health Check
```
GET /health
```
Returns:
```json
{
  "status": "ok",
  "timestamp": "2026-03-31T12:34:56.789123"
}
```

### Pipeline Status
```
GET /api/status
```
Returns:
```json
{
  "status": "ok",
  "query": null,
  "current_hop": null,
  "docs_retrieved": null,
  "docs_blocked": null,
  "timestamp": "2026-03-31T12:34:56.789123"
}
```

### Execute Query (Sync)
```
POST /query
Content-Type: application/json

{
  "query": "What is zero trust?",
  "attack_enabled": false,
  "defence_enabled": true
}
```
Returns:
```json
{
  "answer": "Zero trust is...",
  "hop_count": 3,
  "blocked_docs": 2,
  "hop_queries": ["What is zero trust?", "How to implement?", "..."],
  "total_retrieved": 10
}
```

### Inject Attack
```
POST /api/attack/inject
Content-Type: application/json

{
  "topic": "zero trust",
  "count": 10,
  "collection_name": "documents"
}
```
Returns:
```json
{
  "injected_count": 10,
  "collection_name": "documents",
  "timestamp": "2026-03-31T12:34:56.789123"
}
```

### Get Evaluation Results
```
GET /api/eval/results?limit=10
```
Returns:
```json
{
  "results": {
    "condition_0": { ... },
    "condition_1": { ... },
    ...
  },
  "retrieved_at": "2026-03-31T12:34:56.789123"
}
```

### Get Benchmark Documents
```
GET /api/benchmark/docs?doc_type=clean&limit=10
```

**Query Parameters**:
- `doc_type` (str): One of `all`, `clean`, `injected`, `cascade`, `drift`, `hijack`, `amplification`
- `limit` (int): Maximum documents to return (1-1000, default: 10)

Returns:
```json
{
  "doc_type": "clean",
  "count": 10,
  "docs": [
    {
      "type": "clean",
      "doc": { "content": "...", "source": "..." }
    },
    ...
  ]
}
```

### Get Configuration
```
GET /api/config
```
Returns:
```json
{
  "config": {
    "models": { ... },
    "pipeline": { ... },
    "eval": { ... }
  },
  "loaded_at": "2026-03-31T12:34:56.789123"
}
```

### Root / API Documentation
```
GET /
```
Returns list of all available endpoints.

## CORS Configuration

The API is configured to accept requests from:
- `http://localhost:3000` (React dev server)
- `http://127.0.0.1:3000`

To add more origins, modify in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://your-dashboard.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Running the Server

```bash
# Development (auto-reload)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or directly
python main.py

# Production (with workers)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Architecture

```
React Dashboard (localhost:3000)
    ↓
    ├─→ WebSocket /ws/pipeline (real-time streaming)
    └─→ REST API endpoints (/api/*)
         ↓
    FastAPI Server (0.0.0.0:8000)
         ↓
         ├─→ Pipeline Graph (LangGraph + Qdrant)
         ├─→ Trust Filter (evaluation)
         ├─→ Guardrails (NeMo)
         └─→ Config/Results (YAML/JSON)
```

## Performance Considerations

- **WebSocket**: Each query runs in `asyncio.to_thread()` to avoid blocking other connections
- **Background Tasks**: Attack injection runs in background without blocking HTTP response
- **Streaming**: Hops are streamed with 0.1s delay for realistic UI animation
- **Memory**: Pipeline state is local per connection; connections cleanup on disconnect

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200 OK` - Success
- `400 Bad Request` - Invalid query parameters
- `404 Not Found` - Resource not found (e.g., no results yet)
- `500 Internal Server Error` - Server-side error

WebSocket errors are sent as JSON events with type `"error"`.

## Logging

All requests and events are logged to console with timestamps:
```
2026-03-31 12:34:56,789 - __main__ - INFO - WebSocket client connected
2026-03-31 12:34:56,790 - __main__ - INFO - Received query: What is zero trust...
...
```

## Troubleshooting

### WebSocket Connection Refused
- Verify server is running: `curl http://localhost:8000/health`
- Check firewall/port binding
- Verify React dashboard is on localhost:3000

### CORS Errors
- Check browser console for specific origin
- Add origin to `allow_origins` in main.py
- Verify credentials/headers are allowed

### Empty Results
- Evaluation or benchmark data may not exist yet
- Run: `python eval/ablation.py` to generate results
- Check `results/` directory

## Future Enhancements

- [ ] Per-user WebSocket message queuing
- [ ] Metrics export (Prometheus)
- [ ] Authentication/JWT tokens
- [ ] Rate limiting
- [ ] Connection pool management
- [ ] Structured logging (JSON)
