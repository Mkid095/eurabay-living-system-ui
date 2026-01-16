"""
FastAPI application for active trade management API.

This module creates and configures the FastAPI application with all routes.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Active Trade Management API")
    yield
    logger.info("Shutting down Active Trade Management API")


# Create FastAPI application
app = FastAPI(
    title="EURABAY Active Trade Management API",
    description="REST API for controlling and monitoring active trade management",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "EURABAY Active Trade Management API",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "active_trades": "/api/trades/active",
            "trade_state": "/api/trades/{ticket}/state",
            "close_trade": "/api/trades/{ticket}/close",
            "pause_management": "/api/trades/{ticket}/pause",
            "resume_management": "/api/trades/{ticket}/resume",
            "set_stop_loss": "/api/trades/{ticket}/sl",
            "set_take_profit": "/api/trades/{ticket}/tp",
            "performance": "/api/trades/performance",
            "websocket": "/api/trades/ws/trades",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "active-trade-management-api",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
