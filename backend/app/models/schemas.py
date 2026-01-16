"""
Pydantic schemas for data validation and serialization.
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Trade Schemas
# ============================================================================

class TradeBase(BaseModel):
    """Base schema for trade data."""
    symbol: str = Field(..., description="Trading symbol (e.g., V10, V25)")
    direction: Literal["BUY", "SELL"] = Field(..., description="Trade direction")
    entry_price: float = Field(..., gt=0, description="Entry price")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    lot_size: float = Field(..., gt=0, description="Position size in lots")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence (0-1)")
    strategy_used: str = Field(..., description="Strategy name that generated signal")


class TradeCreate(TradeBase):
    """Schema for creating a new trade."""
    mt5_ticket: Optional[int] = Field(None, description="MT5 ticket number")


class TradeUpdate(BaseModel):
    """Schema for updating a trade."""
    exit_price: Optional[float] = Field(None, gt=0, description="Exit price")
    exit_time: Optional[datetime] = Field(None, description="Exit timestamp")
    profit_loss: Optional[float] = Field(None, description="Profit/loss amount")
    profit_loss_pips: Optional[float] = Field(None, description="Profit/loss in pips")
    status: Literal["OPEN", "CLOSED", "PENDING"] = Field(
        "OPEN",
        description="Trade status"
    )
    stop_loss: Optional[float] = Field(None, gt=0, description="Updated stop loss")
    take_profit: Optional[float] = Field(None, gt=0, description="Updated take profit")


class TradeSchema(TradeBase):
    """Complete trade schema."""
    id: int
    mt5_ticket: Optional[int] = None
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    profit_loss: Optional[float] = None
    profit_loss_pips: Optional[float] = None
    status: Literal["OPEN", "CLOSED", "PENDING"]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Performance Metrics Schemas
# ============================================================================

class PerformanceMetricsBase(BaseModel):
    """Base schema for performance metrics."""
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    winning_trades: int = Field(..., ge=0, description="Number of winning trades")
    losing_trades: int = Field(..., ge=0, description="Number of losing trades")
    win_rate: float = Field(..., ge=0, le=100, description="Win rate percentage")
    total_profit: float = Field(..., description="Total profit amount")
    total_loss: float = Field(..., description="Total loss amount")
    profit_factor: float = Field(..., ge=0, description="Profit factor ratio")
    average_win: float = Field(..., description="Average winning trade")
    average_loss: float = Field(..., description="Average losing trade")
    max_drawdown: float = Field(..., le=0, description="Maximum drawdown")
    max_drawdown_pct: float = Field(..., ge=0, le=100, description="Max drawdown %")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio")
    calmar_ratio: Optional[float] = Field(None, description="Calmar ratio")


class PerformanceMetricsCreate(PerformanceMetricsBase):
    """Schema for creating performance metrics."""
    period: Literal["daily", "weekly", "monthly", "all_time"]
    period_start: datetime
    period_end: datetime


class PerformanceMetricsSchema(PerformanceMetricsBase):
    """Complete performance metrics schema."""
    id: int
    period: str
    period_start: datetime
    period_end: datetime
    equity_curve: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Model Schemas
# ============================================================================

class ModelMetadataBase(BaseModel):
    """Base schema for ML model metadata."""
    model_name: str = Field(..., description="Name of the model")
    model_type: str = Field(..., description="Model type (e.g., XGBoost)")
    model_version: str = Field(..., description="Model version")
    symbol: str = Field(..., description="Symbol this model is for")
    accuracy: float = Field(..., ge=0, le=1, description="Model accuracy")
    precision: float = Field(..., ge=0, le=1, description="Model precision")
    recall: float = Field(..., ge=0, le=1, description="Model recall")
    f1_score: float = Field(..., ge=0, le=1, description="F1 score")
    is_active: bool = Field(True, description="Whether model is active")


class ModelMetadataCreate(ModelMetadataBase):
    """Schema for creating model metadata."""
    training_samples: int = Field(..., ge=0, description="Number of training samples")
    features_used: list[str] = Field(..., description="List of features used")


class ModelMetadataSchema(ModelMetadataBase):
    """Complete model metadata schema."""
    id: int
    training_samples: int
    features_used: str  # JSON string
    file_path: str
    training_time: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Configuration Schemas
# ============================================================================

class ConfigurationBase(BaseModel):
    """Base schema for configuration."""
    config_key: str = Field(..., description="Configuration key")
    config_value: str = Field(..., description="Configuration value (JSON string)")
    description: str = Field(..., description="Configuration description")
    category: str = Field(..., description="Configuration category")


class ConfigurationCreate(ConfigurationBase):
    """Schema for creating configuration."""
    pass


class ConfigurationSchema(ConfigurationBase):
    """Complete configuration schema."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Market Data Schemas
# ============================================================================

class MarketDataBase(BaseModel):
    """Base schema for market data."""
    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(..., description="Data timestamp")
    open_price: float = Field(..., gt=0, description="Open price")
    high_price: float = Field(..., gt=0, description="High price")
    low_price: float = Field(..., gt=0, description="Low price")
    close_price: float = Field(..., gt=0, description="Close price")
    volume: int = Field(..., ge=0, description="Trading volume")


class MarketDataCreate(MarketDataBase):
    """Schema for creating market data."""
    timeframe: str = Field(..., description="Timeframe (e.g., M1, M5, H1)")


class MarketDataSchema(MarketDataBase):
    """Complete market data schema."""
    id: int
    timeframe: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Signal Schemas
# ============================================================================

class SignalBase(BaseModel):
    """Base schema for trading signals."""
    symbol: str = Field(..., description="Trading symbol")
    direction: Literal["BUY", "SELL", "WAIT"] = Field(..., description="Signal direction")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence")
    price: float = Field(..., gt=0, description="Price at signal generation")
    strategy: str = Field(..., description="Strategy name")
    reasons: list[str] = Field(default_factory=list, description="Reasons for signal")


class SignalCreate(SignalBase):
    """Schema for creating a signal."""
    pass


class SignalSchema(SignalBase):
    """Complete signal schema."""
    id: int
    timestamp: datetime
    executed: bool = False
    trade_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# API Response Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database_connected: bool
    mt5_connected: bool
    trading_loop_status: str
    uptime_seconds: float


class AccountInfoResponse(BaseModel):
    """Account information response."""
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    open_positions: int
    total_trades: int


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
