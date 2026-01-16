"""
REST API router for backend endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger

api_router = APIRouter(tags=["REST API"])


# Pydantic models for request/response
class HealthResponse(BaseModel):
    """Health check response model."""
    success: bool
    status: str
    service: str
    version: str


class AccountInfo(BaseModel):
    """Account information model."""
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float


class Position(BaseModel):
    """Trading position model."""
    ticket: int
    symbol: str
    type: str
    volume: float
    price_open: float
    price_current: float
    profit: float
    comment: str


class Trade(BaseModel):
    """Trade history model."""
    ticket: int
    symbol: str
    type: str
    volume: float
    price: float
    profit: float
    commission: float
    swap: float
    closed_time: str


class Signal(BaseModel):
    """Trading signal model."""
    symbol: str
    direction: str
    confidence: float
    timestamp: str
    reasons: List[str]


class ModelInfo(BaseModel):
    """Model information model."""
    name: str
    version: str
    accuracy: float
    last_trained: str
    status: str


class Config(BaseModel):
    """Configuration model."""
    trading_enabled: bool
    paper_trading: bool
    max_risk_per_trade: float
    max_daily_loss: float
    max_concurrent_positions: int


# Endpoints

@api_router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """
    Health check endpoint for monitoring.

    Returns system status and version information.
    """
    return HealthResponse(
        success=True,
        status="healthy",
        service="eurabay-living-system",
        version=settings.VERSION
    )


@api_router.get("/account", response_model=AccountInfo)
async def get_account() -> AccountInfo:
    """
    Get account information including balance, equity, and margin.

    Note: Returns placeholder values until MT5 integration is complete.
    """
    # Placeholder values - will be replaced with MT5 data
    return AccountInfo(
        balance=10000.0,
        equity=10000.0,
        margin=0.0,
        free_margin=10000.0,
        margin_level=0.0,
        profit=0.0
    )


@api_router.get("/positions")
async def get_positions() -> List[Position]:
    """
    Get all open trading positions.

    Note: Returns empty list until MT5 integration is complete.
    """
    # Placeholder - will be replaced with MT5 data
    return []


@api_router.get("/trades")
async def get_trades(limit: int = 100) -> List[Trade]:
    """
    Get trade history.

    Note: Returns empty list until database integration is complete.
    """
    # Placeholder - will be replaced with database query
    return []


@api_router.get("/performance")
async def get_performance() -> dict:
    """
    Get performance metrics including win rate, profit factor, and drawdown.

    Note: Returns placeholder values until performance tracking is complete.
    """
    # Placeholder values
    return {
        "success": True,
        "metrics": {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "profitable_trades": 0,
            "losing_trades": 0
        }
    }


@api_router.get("/signals")
async def get_signals(limit: int = 50) -> List[Signal]:
    """
    Get recent trading signals.

    Note: Returns empty list until signal generation is complete.
    """
    # Placeholder - will be replaced with database query
    return []


@api_router.get("/models")
async def get_models() -> List[ModelInfo]:
    """
    Get information about trained ML models.

    Note: Returns empty list until model training is complete.
    """
    # Placeholder - will be replaced with model data
    return []


@api_router.post("/start")
async def start_trading() -> dict:
    """
    Start the autonomous trading loop.

    Note: Placeholder until trading loop implementation.
    """
    logger.info("Trading start requested")
    return {
        "success": True,
        "message": "Trading loop start requested",
        "status": "starting"
    }


@api_router.post("/stop")
async def stop_trading() -> dict:
    """
    Stop the autonomous trading loop.

    Note: Placeholder until trading loop implementation.
    """
    logger.info("Trading stop requested")
    return {
        "success": True,
        "message": "Trading loop stop requested",
        "status": "stopping"
    }


@api_router.post("/pause")
async def pause_trading() -> dict:
    """
    Pause the autonomous trading loop.

    Note: Placeholder until trading loop implementation.
    """
    logger.info("Trading pause requested")
    return {
        "success": True,
        "message": "Trading loop pause requested",
        "status": "paused"
    }


@api_router.get("/config", response_model=Config)
async def get_config() -> Config:
    """
    Get current system configuration.
    """
    return Config(
        trading_enabled=settings.TRADING_ENABLED,
        paper_trading=settings.PAPER_TRADING,
        max_risk_per_trade=settings.MAX_RISK_PER_TRADE,
        max_daily_loss=settings.MAX_DAILY_LOSS,
        max_concurrent_positions=settings.MAX_CONCURRENT_POSITIONS
    )


@api_router.put("/config")
async def update_config(config: Config) -> dict:
    """
    Update system configuration.

    Note: Placeholder until configuration management is complete.
    """
    logger.info(f"Configuration update requested: {config}")
    return {
        "success": True,
        "message": "Configuration updated",
        "config": config.dict()
    }
