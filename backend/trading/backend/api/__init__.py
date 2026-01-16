"""
API package for active trade management.

This package provides REST API and WebSocket endpoints for
controlling and monitoring active trade management.
"""

from .routes import router

__all__ = ["router"]
