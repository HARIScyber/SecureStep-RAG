# WebSocket API Setup & Deployment Guide

## Prerequisites

Ensure your `pyproject.toml` includes these core dependencies (already present):
- `fastapi >= 0.115.0` - Web framework with WebSocket support
- `uvicorn[standard] >= 0.32.0` - ASGI server
- `pydantic >= 2.9.2` - Data validation
- `pyyaml >= 6.0.2` - Configuration loading

## Installation

```bash
# Install/update dependencies
poetry install
# or
pip install fastapi uvicorn pydantic pyyaml

# Verify installation
python -c "import fastapi; from fastapi import WebSocket; print('✓ FastAPI WebSocket support OK')"
```

## Running the Server

### Development (with auto-reload)
```bash
# Using Poetry
poetry run python main.py

# Or directly with uvicorn
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production (with multiple workers)
```bash
# Using uvicorn with 4 worker processes
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using Gunicorn + Uvicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY . .

EXPOSE 8000
CMD ["python", "main.py"]
```

```bash
# Build and run
docker build -t securestep-rag .
docker run -p 8000:8000 securestep-rag
```

## Testing the API

### 1. Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "timestamp": "..."}
```

### 2. WebSocket Streaming (Python)
```python
import asyncio
import json
import websockets

async def test_websocket():
    async with websockets.connect("ws://localhost:8000/ws/pipeline") as ws:
        # Send query
        await ws.send(json.dumps({
            "query": "What is zero trust?",
            "attack_enabled": False,
            "defence_enabled": True,
        }))
        
        # Receive messages
        while True:
            try:
                msg = await ws.recv()
                print(json.loads(msg))
            except Exception as e:
                break

asyncio.run(test_websocket())
```

### 3. WebSocket Streaming (JavaScript/Node.js)
```bash
npm install ws  # Install WebSocket client

# Create test-ws.js
cat > test-ws.js << 'EOF'
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/pipeline');

ws.on('open', () => {
  console.log('Connected');
  ws.send(JSON.stringify({
    query: "What is zero trust?",
    attack_enabled: false,
    defence_enabled: true,
  }));
});

ws.on('message', (data) => {
  console.log('Received:', JSON.parse(data));
});

ws.on('error', (err) => console.error('Error:', err));
ws.on('close', () => console.log('Disconnected'));
EOF

node test-ws.js
```

### 4. REST API Endpoints
```bash
# Get status
curl http://localhost:8000/api/status

# Execute query (sync)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is zero trust?", "attack_enabled": false, "defence_enabled": true}'

# Get eval results
curl http://localhost:8000/api/eval/results

# Get benchmark docs
curl "http://localhost:8000/api/benchmark/docs?doc_type=clean&limit=5"

# Get config
curl http://localhost:8000/api/config

# API documentation
curl http://localhost:8000/
```

## CORS Configuration

The server is configured for development with React dashboard on `localhost:3000`.

**For production**, update the CORS origins in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Environment Variables

Create `.env` file:
```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
MODEL_PROVIDER=openai

# Qdrant Vector Store
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...

# Logging
LOG_LEVEL=INFO

# Port
PORT=8000
```

Load with:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Performance Tuning

### 1. Connection Pool Settings
```python
# In main.py - increase limits for high concurrency
from fastapi import FastAPI

app = FastAPI(
    title="SecureStep-RAG",
    max_concurrent_connections=100,  # WebSocket connections
)
```

### 2. Uvicorn Workers
```bash
# For CPU-bound pipeline work (1 worker per CPU core)
python -m uvicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# For I/O-bound work (more workers ok)
python -m uvicorn main:app --workers 16
```

### 3. Async Optimization
The pipeline execution runs in a thread pool to avoid blocking:
```python
result = await asyncio.to_thread(
    _stream_pipeline_execution,  # CPU-intensive
    query,
    attack_enabled,
    defence_enabled,
    attack_type,
)
```

## Monitoring & Logging

### 1. Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Request/Response Logging
```python
from fastapi import Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response
```

### 3. Metrics Export (Prometheus)
```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    request_count.labels(method=request.method, endpoint=request.url.path).inc()
    with request_duration.time():
        response = await call_next(request)
    return response
```

## Troubleshooting

### WebSocket Hangs on Connection
```
Problem: WebSocket /ws/pipeline takes forever to stream
Solution: Check if pipeline.run() is blocking
  - Add logging to _stream_pipeline_execution()
  - Verify Qdrant/LLM services are reachable
  - Increase timeout: ws_timeout = 300
```

### Memory Leak on Long Connections
```
Problem: Memory grows with each WebSocket connection
Solution:
  - Close connections properly with ws.close()
  - Cleanup in finally block
  - Monitor with: watch -n 1 'ps aux | grep main.py'
```

### CORS Errors in Browser
```
Problem: OPTIONS /ws/pipeline → 403 Forbidden
Solution: CORS middleware only applies to HTTP, not WebSocket
  - Check browser console for actual origin
  - Verify React app is on allowed origin (localhost:3000)
  - Add origin to allow_origins list
```

### High CPU Usage
```
Problem: CPU spikes when streaming
Solution:
  - Add delay between stream updates: await asyncio.sleep(0.1)
  - Use fewer workers: --workers 1
  - Profile with: python -m cProfile main.py
```

## Integration with React Dashboard

### Installation
```bash
# Create React app
npx create-react-app securestep-dashboard --template typescript

# Install dependencies
cd securestep-dashboard
npm install axios

# Copy PipelineStreamer component
cp ../dashboard/PipelineStreamer.tsx src/components/
```

### Usage
```tsx
// src/App.tsx
import { PipelineStreamer } from './components/PipelineStreamer';

function App() {
  return (
    <div className="App">
      <PipelineStreamer />
    </div>
  );
}

export default App;
```

### Run
```bash
# Start React (http://localhost:3000)
npm start

# Start API server in another terminal (http://localhost:8000)
python main.py
```

## Production Deployment

### Option 1: AWS EC2 + Gunicorn
```bash
# Install
sudo apt-get update
sudo apt-get install python3.11 python3-pip

# Deploy
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 --access-logfile - --error-logfile -
```

### Option 2: Docker Compose
```yaml
version: '3'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  dashboard:
    build: ./dashboard
    ports:
      - "3000:3000"

volumes:
  qdrant_data:
```

```bash
docker-compose up -d
```

### Option 3: Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: securestep-rag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: securestep-rag
  template:
    metadata:
      labels:
        app: securestep-rag
    spec:
      containers:
      - name: api
        image: securestep-rag:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_PROVIDER
          value: "openai"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: openai-key
```

## Health Checks

### Liveness Probe
```bash
curl http://localhost:8000/health
```

### Readiness Probe
```bash
curl http://localhost:8000/api/status
```

### Startup Probe
```bash
# Verify models are loaded
curl http://localhost:8000/api/config | jq '.config.models'
```

## Performance Baseline

Typical results on MacBook Pro M2:

| Operation | Latency | Notes |
|-----------|---------|-------|
| `/health` | 1ms | Direct response |
| `/query` (1-hop) | 500-2000ms | Depends on LLM |
| `/ws/pipeline` (3-hop) | 3000-8000ms | With streaming |
| `/api/eval/results` | 50-200ms | File I/O |

## Next Steps

1. ✅ Update `main.py` with WebSocket endpoints
2. ✅ Update CORS for React dashboard
3. ✅ Test WebSocket streaming
4. ⬜ Add authentication (JWT tokens)
5. ⬜ Add rate limiting
6. ⬜ Add metrics export (Prometheus)
7. ⬜ Deploy to production
