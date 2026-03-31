#!/usr/bin/env python3
"""Verification script for WebSocket API implementation."""

import sys
from pathlib import Path

def check_file_exists(path: str) -> bool:
    """Check if file exists."""
    exists = Path(path).exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {path}")
    return exists

def check_imports():
    """Check if required imports work."""
    print("\n📦 Checking imports...")
    try:
        from fastapi import FastAPI, WebSocket
        print("  ✓ FastAPI + WebSocket")
    except ImportError as e:
        print(f"  ✗ FastAPI: {e}")
        return False
    
    try:
        from pydantic import BaseModel
        print("  ✓ Pydantic")
    except ImportError as e:
        print(f"  ✗ Pydantic: {e}")
        return False
    
    try:
        import uvicorn
        print("  ✓ Uvicorn")
    except ImportError as e:
        print(f"  ✗ Uvicorn: {e}")
        return False
    
    try:
        import yaml
        print("  ✓ PyYAML")
    except ImportError as e:
        print(f"  ✗ PyYAML: {e}")
        return False
    
    return True

def check_syntax():
    """Check main.py syntax."""
    print("\n✅ Checking syntax...")
    import ast
    import subprocess
    
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", "main.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("  ✓ main.py syntax valid")
        else:
            print(f"  ✗ main.py syntax error:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"  ✗ Syntax check failed: {e}")
        return False
    
    return True

def check_files():
    """Check all required files exist."""
    print("\n📁 Checking files...")
    
    required_files = [
        "main.py",
        "WEBSOCKET_API.md",
        "DEPLOYMENT.md",
        "WEBSOCKET_IMPLEMENTATION.md",
        "dashboard/PipelineStreamer.tsx",
        "tests/test_main_api.py",
        "quick-start.bat",
        "quick-start.sh",
    ]
    
    all_exist = True
    for file_path in required_files:
        if not check_file_exists(file_path):
            all_exist = False
    
    return all_exist

def check_makefile():
    """Check Makefile has new targets."""
    print("\n⚙️  Checking Makefile...")
    
    required_targets = [
        "run",
        "run-prod",
        "test-api",
        "docs",
        "health",
        "status",
        "config",
    ]
    
    try:
        with open("Makefile") as f:
            content = f.read()
        
        all_present = True
        for target in required_targets:
            if target in content:
                print(f"  ✓ {target}")
            else:
                print(f"  ✗ {target}")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"  ✗ Error reading Makefile: {e}")
        return False

def check_endpoints():
    """Check main.py has required endpoints."""
    print("\n🔌 Checking endpoints...")
    
    required_endpoints = [
        "/health",
        "/ws/pipeline",
        "/api/status",
        "/query",
        "/api/attack/inject",
        "/api/eval/results",
        "/api/benchmark/docs",
        "/api/config",
    ]
    
    try:
        with open("main.py") as f:
            content = f.read()
        
        all_present = True
        for endpoint in required_endpoints:
            if endpoint in content:
                print(f"  ✓ {endpoint}")
            else:
                print(f"  ✗ {endpoint}")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"  ✗ Error reading main.py: {e}")
        return False

def check_pydantic_models():
    """Check Pydantic models are defined."""
    print("\n📋 Checking Pydantic models...")
    
    required_models = [
        "QueryRequest",
        "WebSocketMessage",
        "HopStartEvent",
        "DocRetrievedEvent",
        "AnswerEvent",
        "ErrorEvent",
        "PipelineStatus",
        "AttackInjectionRequest",
        "AttackInjectionResult",
    ]
    
    try:
        with open("main.py") as f:
            content = f.read()
        
        all_present = True
        for model in required_models:
            if model in content:
                print(f"  ✓ {model}")
            else:
                print(f"  ✗ {model}")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"  ✗ Error reading main.py: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 70)
    print("🔍 SecureStep-RAG WebSocket API Verification")
    print("=" * 70)
    
    results = {
        "Files": check_files(),
        "Imports": check_imports(),
        "Syntax": check_syntax(),
        "Makefile": check_makefile(),
        "Endpoints": check_endpoints(),
        "Models": check_pydantic_models(),
    }
    
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✓" if result else "✗"
        print(f"{status} {check}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed! Ready to run:")
        print("   make run          # Development server")
        print("   make run-prod     # Production server")
        print("   make test-api     # Run API tests")
        print("   make docs         # Open API documentation")
        return 0
    else:
        print(f"\n❌ {total - passed} check(s) failed. Review output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
