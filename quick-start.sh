#!/usr/bin/env bash
# quick-start.sh - Start SecureStep-RAG API server with WebSocket streaming

set -e

echo "🚀 SecureStep-RAG Quick Start"
echo "=============================="

# Check Python
echo "✓ Checking Python installation..."
python --version || { echo "❌ Python not found"; exit 1; }

# Install dependencies
echo "✓ Installing dependencies..."
pip install fastapi uvicorn pydantic pyyaml >/dev/null 2>&1 || {
    echo "❌ Failed to install dependencies"
    exit 1
}

# Verify imports
echo "✓ Verifying imports..."
python -c "from fastapi import FastAPI, WebSocket; print('  ✓ FastAPI with WebSocket support')" || {
    echo "❌ FastAPI import failed"
    exit 1
}

# Check main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in current directory"
    exit 1
fi

echo ""
echo "📝 Configuration"
echo "================"
echo "API Server:     http://localhost:8000"
echo "WebSocket:      ws://localhost:8000/ws/pipeline"
echo "Documentation:  http://localhost:8000/docs"
echo "ReDoc:          http://localhost:8000/redoc"
echo ""
echo "CORS configured for:"
echo "  - http://localhost:3000 (React dashboard)"
echo "  - http://127.0.0.1:3000"
echo ""

# Start server
echo "🌐 Starting FastAPI server..."
echo "=============================="
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Note: If you want to disable auto-reload, use:
# python -m uvicorn main:app --host 0.0.0.0 --port 8000
