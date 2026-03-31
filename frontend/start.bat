@echo off
REM Quick start script for SecureStep-RAG frontend on Windows

echo 🚀 SecureStep-RAG Frontend - Quick Start
echo ==========================================

REM Check Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js 16+ first.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo ✓ Node.js %NODE_VERSION%

REM Install dependencies
echo.
echo 📦 Installing dependencies...
call npm install

REM Start dev server
echo.
echo ✨ Starting dev server...
echo.
echo 🌍 Dashboard: http://localhost:3000
echo 📡 Backend: http://localhost:8000
echo.
echo Press Ctrl+C to stop
echo.

call npm run dev
pause
