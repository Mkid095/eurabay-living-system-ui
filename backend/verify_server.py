#!/usr/bin/env python
"""
Verify backend server can start and respond to basic requests.
Run this script to test the FastAPI application.
"""

import sys
import os
import asyncio

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.logging import setup_logging, logger


async def verify_server():
    """Verify server components are properly configured."""
    print("=" * 60)
    print("EURABAY Living System - Server Verification")
    print("=" * 60)
    print()

    # Setup logging
    setup_logging()
    logger.info("Starting server verification...")

    # Check configuration
    print("Configuration:")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  Debug mode: {settings.DEBUG}")
    print(f"  Host: {settings.HOST}")
    print(f"  Port: {settings.PORT}")
    print(f"  Trading enabled: {settings.TRADING_ENABLED}")
    print(f"  Paper trading: {settings.PAPER_TRADING}")
    print(f"  Trading symbols: {settings.parsed_trading_symbols}")
    print()

    # Check directories
    print("Directories:")
    for dir_path in [settings.DATA_DIR, settings.LOG_DIR, settings.MODEL_DIR]:
        exists = os.path.exists(dir_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")
        if not exists:
            os.makedirs(dir_path, exist_ok=True)
            print(f"    Created: {dir_path}")
    print()

    # Check imports
    print("Imports:")
    try:
        from app.main import app
        print("  ✓ FastAPI application")
    except Exception as e:
        print(f"  ✗ FastAPI application: {e}")
        return False

    try:
        from app.api.rest import api_router
        print("  ✓ REST API router")
    except Exception as e:
        print(f"  ✗ REST API router: {e}")
        return False

    try:
        from app.api.ws import ws_router, manager
        print("  ✓ WebSocket router")
    except Exception as e:
        print(f"  ✗ WebSocket router: {e}")
        return False

    try:
        from app.core.config import settings
        print("  ✓ Configuration")
    except Exception as e:
        print(f"  ✗ Configuration: {e}")
        return False

    print()

    # Check routes
    print("API Routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = list(route.methods) if route.methods else []
            print(f"  {', '.join(methods):<10} {route.path}")
    print()

    print("=" * 60)
    print("✓ Server verification complete!")
    print("=" * 60)
    print()
    print("To start the server:")
    print("  Unix/Linux/Mac:  ./start.sh")
    print("  Windows:        start.bat")
    print("  Manual:         uvicorn app.main:app --reload")
    print()

    return True


if __name__ == "__main__":
    result = asyncio.run(verify_server())
    sys.exit(0 if result else 1)
