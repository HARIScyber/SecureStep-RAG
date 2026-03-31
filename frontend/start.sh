#!/bin/bash
# Quick start script for SecureStep-RAG frontend

echo "🚀 SecureStep-RAG Frontend - Quick Start"
echo "=========================================="

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✓ Node.js $(node -v)"

# Navigate to frontend
cd "$(dirname "$0")" || exit

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Start dev server
echo ""
echo "✨ Starting dev server..."
echo ""
echo "🌍 Dashboard: http://localhost:3000"
echo "📡 Backend: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev
