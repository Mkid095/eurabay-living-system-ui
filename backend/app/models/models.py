"""
SQLAlchemy async models for EURABAY Living System database.
All models support async operations via aiosqlite.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, Text, Index,
    ForeignKey, JSON, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


# ============================================================================
# Trade Model
# ============================================================================

class Trade(Base):
    """
    Trade model for storing all trading activity.
    Tracks entries, exits, and performance of each trade.
    """
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mt5_ticket: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        index=True,
        comment="MT5 ticket number for the trade"
    )
    symbol: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Trading symbol (e.g., V10, V25, V50, V75, V100)"
    )
    direction: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        comment="Trade direction: BUY or SELL"
    )
    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Entry price"
    )
    entry_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Entry timestamp"
    )
    exit_price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Exit price"
    )
    exit_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        comment="Exit timestamp"
    )
    stop_loss: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Stop loss price"
    )
    take_profit: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Take profit price"
    )
    lot_size: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Position size in lots"
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Signal confidence (0-1)"
    )
    strategy_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Strategy name that generated the signal"
    )
    profit_loss: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Profit/loss in account currency"
    )
    profit_loss_pips: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Profit/loss in pips"
    )
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="OPEN",
        index=True,
        comment="Trade status: OPEN, CLOSED, PENDING"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record update timestamp"
    )

    __table_args__ = (
        Index("ix_trades_symbol_status", "symbol", "status"),
        Index("ix_trades_entry_time", "entry_time"),
        CheckConstraint("direction IN ('BUY', 'SELL')", name="check_trade_direction"),
        CheckConstraint("status IN ('OPEN', 'CLOSED', 'PENDING')", name="check_trade_status"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_confidence_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<Trade(id={self.id}, symbol={self.symbol}, "
            f"direction={self.direction}, status={self.status})>"
        )


# ============================================================================
# Performance Metrics Model
# ============================================================================

class PerformanceMetrics(Base):
    """
    Performance metrics model for tracking system performance.
    Stores aggregated metrics for different time periods.
    """
    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Time period: daily, weekly, monthly, all_time"
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="Period start timestamp"
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="Period end timestamp"
    )
    total_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of trades"
    )
    winning_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of winning trades"
    )
    losing_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of losing trades"
    )
    win_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Win rate percentage (0-100)"
    )
    total_profit: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Total profit amount"
    )
    total_loss: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Total loss amount"
    )
    profit_factor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Profit factor ratio (gross profit / gross loss)"
    )
    average_win: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Average winning trade amount"
    )
    average_loss: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Average losing trade amount"
    )
    max_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Maximum drawdown amount"
    )
    max_drawdown_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Maximum drawdown percentage"
    )
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Sharpe ratio"
    )
    sortino_ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Sortino ratio"
    )
    calmar_ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Calmar ratio"
    )
    equity_curve: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Equity curve data points"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record update timestamp"
    )

    __table_args__ = (
        Index("ix_performance_period", "period", "period_start", "period_end"),
        CheckConstraint("win_rate >= 0 AND win_rate <= 100", name="check_win_rate_range"),
        CheckConstraint("period IN ('daily', 'weekly', 'monthly', 'all_time')", name="check_period_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<PerformanceMetrics(id={self.id}, period={self.period}, "
            f"win_rate={self.win_rate}%, profit_factor={self.profit_factor})>"
        )


# ============================================================================
# Model Metadata Model
# ============================================================================

class ModelMetadata(Base):
    """
    ML model metadata for tracking trained models.
    Stores model performance, versions, and file locations.
    """
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Name of the model"
    )
    model_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model type (e.g., XGBoost, RandomForest)"
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model version identifier"
    )
    symbol: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Symbol this model is trained for"
    )
    training_samples: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of training samples used"
    )
    features_used: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON string of features used"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Path to saved model file"
    )
    accuracy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Model accuracy (0-1)"
    )
    precision: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Model precision (0-1)"
    )
    recall: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Model recall (0-1)"
    )
    f1_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Model F1 score (0-1)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this model is currently active"
    )
    training_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Training completion timestamp"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record update timestamp"
    )

    __table_args__ = (
        Index("ix_models_symbol_active", "symbol", "is_active"),
        Index("ix_models_name_version", "model_name", "model_version"),
        CheckConstraint("accuracy >= 0 AND accuracy <= 1", name="check_accuracy_range"),
        CheckConstraint("precision >= 0 AND precision <= 1", name="check_precision_range"),
        CheckConstraint("recall >= 0 AND recall <= 1", name="check_recall_range"),
        CheckConstraint("f1_score >= 0 AND f1_score <= 1", name="check_f1_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<ModelMetadata(id={self.id}, name={self.model_name}, "
            f"version={self.model_version}, symbol={self.symbol}, "
            f"active={self.is_active})>"
        )


# ============================================================================
# Configuration Model
# ============================================================================

class Configuration(Base):
    """
    Configuration model for system settings.
    Stores runtime configuration that can be updated without code changes.
    """
    __tablename__ = "configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique configuration key"
    )
    config_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Configuration value (JSON string for complex values)"
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Human-readable description"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Configuration category (e.g., risk, trading, system)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this configuration is active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record update timestamp"
    )

    __table_args__ = (
        Index("ix_config_category", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<Configuration(id={self.id}, key={self.config_key}, "
            f"category={self.category})>"
        )


# ============================================================================
# Market Data Model
# ============================================================================

class MarketData(Base):
    """
    Market data model for storing OHLCV price data.
    Used for historical analysis and feature engineering.
    """
    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Trading symbol"
    )
    timeframe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Timeframe (e.g., M1, M5, M15, H1, H4, D1)"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="Candle timestamp"
    )
    open_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Open price"
    )
    high_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="High price"
    )
    low_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Low price"
    )
    close_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Close price"
    )
    volume: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Trading volume"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )

    __table_args__ = (
        Index("ix_market_data_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp"),
        Index("ix_market_data_timestamp", "timestamp"),
        CheckConstraint("high_price >= low_price", name="check_high_low"),
        CheckConstraint("high_price >= open_price", name="check_high_open"),
        CheckConstraint("high_price >= close_price", name="check_high_close"),
        CheckConstraint("low_price <= open_price", name="check_low_open"),
        CheckConstraint("low_price <= close_price", name="check_low_close"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketData(id={self.id}, symbol={self.symbol}, "
            f"timeframe={self.timeframe}, timestamp={self.timestamp})>"
        )


# ============================================================================
# Signal Model
# ============================================================================

class Signal(Base):
    """
    Signal model for tracking trading signals generated by the system.
    Logs all signals for audit trail and analysis.
    """
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Trading symbol"
    )
    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Signal direction: BUY, SELL, WAIT"
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Signal confidence (0-1)"
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Price at signal generation"
    )
    strategy: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Strategy that generated the signal"
    )
    reasons: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of reasons for the signal"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Signal generation timestamp"
    )
    executed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether signal was executed"
    )
    trade_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trades.id"),
        nullable=True,
        comment="Associated trade ID if executed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )

    __table_args__ = (
        Index("ix_signals_symbol_timestamp", "symbol", "timestamp"),
        Index("ix_signals_executed", "executed"),
        CheckConstraint("direction IN ('BUY', 'SELL', 'WAIT')", name="check_signal_direction"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_signal_confidence"),
    )

    def __repr__(self) -> str:
        return (
            f"<Signal(id={self.id}, symbol={self.symbol}, "
            f"direction={self.direction}, confidence={self.confidence})>"
        )
