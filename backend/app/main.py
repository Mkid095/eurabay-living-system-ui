"""
EURABAY Living System - Main FastAPI Application
Trading system backend for volatility indices (V10, V25, V50, V75, V100)
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import sys
import os
import uuid

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.ws import ws_router
from app.api.rest import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting EURABAY Living System backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Validate configuration
    try:
        settings.validate_configuration()
        logger.info("Configuration validation passed")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down EURABAY Living System backend...")


# Create FastAPI application
app = FastAPI(
    title="EURABAY Living System API",
    description="Autonomous trading system for volatility indices",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request size limiting
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Limit request size to MAX_REQUEST_SIZE."""
    content_length = request.headers.get("content-length")
    if content_length:
        content_length = int(content_length)
        if content_length > settings.MAX_REQUEST_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "success": False,
                    "error": "Request too large",
                    "detail": f"Request size {content_length} exceeds maximum {settings.MAX_REQUEST_SIZE}"
                }
            )
    return await call_next(request)


# Middleware for request ID tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracking and logging."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Include routers
app.include_router(ws_router, prefix="/ws")
app.include_router(api_router, prefix="/api")


# Health check endpoint
@app.get("/", tags=["Health"])
async def root() -> dict:
    """Root endpoint with basic system information."""
    return {
        "success": True,
        "message": "EURABAY Living System API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint for monitoring."""
    return {
        "success": True,
        "status": "healthy",
        "service": "eurabay-living-system",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        timeout_keep_alive=settings.CONNECTION_TIMEOUT,
        timeout_graceful_shutdown=settings.READ_TIMEOUT,
        limit_max_request_size=settings.MAX_REQUEST_SIZE,
    )
