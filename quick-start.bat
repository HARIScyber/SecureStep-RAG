@echo off
REM quick-start.bat - Start SecureStep-RAG API server with WebSocket streaming (Windows)

setlocal enabledelayedexpansion

echo.
echo 🚀 SecureStep-RAG Quick Start
echo ==============================

REM Check Python
echo ✓ Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found
    exit /b 1
)

REM Install dependencies
echo ✓ Installing dependencies...
pip install fastapi uvicorn pydantic pyyaml >nul 2>&1
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

REM Verify imports
echo ✓ Verifying imports...
python -c "from fastapi import FastAPI, WebSocket; print('  ✓ FastAPI with WebSocket support')" >nul 2>&1
if errorlevel 1 (
    echo ❌ FastAPI import failed
    exit /b 1
)

REM Check main.py exists
if not exist "main.py" (
    echo ❌ main.py not found in current directory
    exit /b 1
)

echo.
echo 📝 Configuration
echo ================
echo API Server:     http://localhost:8000
echo WebSocket:      ws://localhost:8000/ws/pipeline
echo Documentation:  http://localhost:8000/docs
echo ReDoc:          http://localhost:8000/redoc
echo.
echo CORS configured for:
echo   - http://localhost:3000 ^(React dashboard^)
echo   - http://127.0.0.1:3000
echo.

REM Start server
echo 🌐 Starting FastAPI server...
echo ==============================
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

REM Note: If you want to disable auto-reload, use:
REM python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
