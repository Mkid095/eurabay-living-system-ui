"""
Adaptive Risk Manager for performance-based position sizing.

This module implements adaptive risk management that adjusts position sizes
based on recent trading performance to survive losing streaks and maximize
winning streaks.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

from .trade_state import TradePosition
from .performance_comparator import PerformanceComparator, TradeOutcome


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RiskAdjustment:
    """
    Record of a risk adjustment.

    Attributes:
        timestamp: When the adjustment occurred
        old_risk_percent: Previous risk percentage
        new_risk_percent: New risk percentage
        adjustment_type: Type of adjustment (performance, drawdown, etc.)
        win_rate: Win rate that triggered the adjustment
        reason: Explanation for the adjustment
    """

    timestamp: datetime
    old_risk_percent: float
    new_risk_percent: float
    adjustment_type: str
    win_rate: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "old_risk_percent": round(self.old_risk_percent, 2),
            "new_risk_percent": round(self.new_risk_percent, 2),
            "adjustment_type": self.adjustment_type,
            "win_rate": round(self.win_rate, 2),
            "reason": self.reason,
        }


@dataclass
class VolatilityAdjustment:
    """
    Record of a volatility-based position size adjustment.

    Attributes:
        timestamp: When the adjustment occurred
        symbol: Trading symbol
        current_atr: Current ATR value
        average_atr: Average ATR over lookback period
        volatility_ratio: Ratio of current to average ATR
        volatility_multiplier: Position size multiplier applied
        reason: Explanation for the adjustment
    """

    timestamp: datetime
    symbol: str
    current_atr: float
    average_atr: float
    volatility_ratio: float
    volatility_multiplier: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "current_atr": round(self.current_atr, 6),
            "average_atr": round(self.average_atr, 6),
            "volatility_ratio": round(self.volatility_ratio, 3),
            "volatility_multiplier": round(self.volatility_multiplier, 3),
            "reason": self.reason,
        }


@dataclass
class DrawdownAdjustment:
    """
    Record of a drawdown-based risk adjustment.

    Attributes:
        timestamp: When the adjustment occurred
        old_risk_percent: Previous risk percentage
        new_risk_percent: New risk percentage
        current_drawdown: Current drawdown percentage
        peak_equity: Peak equity value
        current_equity: Current equity value
        reason: Explanation for the adjustment
    """

    timestamp: datetime
    old_risk_percent: float
    new_risk_percent: float
    current_drawdown: float
    peak_equity: float
    current_equity: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "old_risk_percent": round(self.old_risk_percent, 2),
            "new_risk_percent": round(self.new_risk_percent, 2),
            "current_drawdown": round(self.current_drawdown, 2),
            "peak_equity": round(self.peak_equity, 2),
            "current_equity": round(self.current_equity, 2),
            "reason": self.reason,
        }


@dataclass
class CorrelationAdjustment:
    """
    Record of a correlation-based risk adjustment.

    Attributes:
        timestamp: When the adjustment occurred
        symbol: Symbol being evaluated for new position
        correlated_symbols: List of symbols highly correlated with the new symbol
        correlation_count: Number of correlated positions already open
        adjustment_multiplier: Position size multiplier applied
        reason: Explanation for the adjustment
    """

    timestamp: datetime
    symbol: str
    correlated_symbols: list[str]
    correlation_count: int
    adjustment_multiplier: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "correlated_symbols": self.correlated_symbols,
            "correlation_count": self.correlation_count,
            "adjustment_multiplier": round(self.adjustment_multiplier, 3),
            "reason": self.reason,
        }


@dataclass
class SessionRiskAdjustment:
    """
    Record of a time-based session risk adjustment.

    Attributes:
        timestamp: When the adjustment occurred
        hour: Hour of day (0-23)
        day_of_week: Day of week (0=Monday, 6=Sunday)
        risk_multiplier: Risk multiplier applied based on time
        reason: Explanation for the adjustment
    """

    timestamp: datetime
    hour: int
    day_of_week: int
    risk_multiplier: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "hour": self.hour,
            "day_of_week": self.day_of_week,
            "risk_multiplier": round(self.risk_multiplier, 3),
            "reason": self.reason,
        }


@dataclass
class DynamicStopAdjustment:
    """
    Record of a dynamic stop loss adjustment.

    Attributes:
        timestamp: When the stop was calculated
        symbol: Trading symbol
        entry_price: Entry price for the position
        direction: "BUY" or "SELL"
        current_atr: Current ATR value
        atr_multiplier: ATR multiplier used for stop calculation
        volatility_regime: Detected volatility regime (low, normal, high)
        calculated_stop: The calculated stop loss price
        stop_distance_pct: Stop distance as percentage of price
        reason: Explanation for the stop calculation
    """

    timestamp: datetime
    symbol: str
    entry_price: float
    direction: str
    current_atr: float
    atr_multiplier: float
    volatility_regime: str
    calculated_stop: float
    stop_distance_pct: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "entry_price": round(self.entry_price, 6),
            "direction": self.direction,
            "current_atr": round(self.current_atr, 6),
            "atr_multiplier": round(self.atr_multiplier, 3),
            "volatility_regime": self.volatility_regime,
            "calculated_stop": round(self.calculated_stop, 6),
            "stop_distance_pct": round(self.stop_distance_pct, 4),
            "reason": self.reason,
        }


@dataclass
class ProfitTargetAdjustment:
    """
    Record of a profit target (take profit) adjustment.

    Attributes:
        timestamp: When the TP was calculated
        symbol: Trading symbol
        entry_price: Entry price for the position
        direction: "BUY" or "SELL"
        current_atr: Current ATR value
        win_rate: Current win rate used for TP calculation
        atr_multiplier: ATR multiplier used for TP calculation
        calculated_tp: The calculated take profit price
        tp_distance_pct: TP distance as percentage of price
        reason: Explanation for the TP calculation
    """

    timestamp: datetime
    symbol: str
    entry_price: float
    direction: str
    current_atr: float
    win_rate: float
    atr_multiplier: float
    calculated_tp: float
    tp_distance_pct: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "entry_price": round(self.entry_price, 6),
            "direction": self.direction,
            "current_atr": round(self.current_atr, 6),
            "win_rate": round(self.win_rate, 2),
            "atr_multiplier": round(self.atr_multiplier, 3),
            "calculated_tp": round(self.calculated_tp, 6),
            "tp_distance_pct": round(self.tp_distance_pct, 4),
            "reason": self.reason,
        }


class AdaptiveRiskManager:
    """
    Manages adaptive risk based on recent trading performance and market volatility.

    Features:
    - Calculates base risk percentage (default 2%)
    - Adjusts risk based on recent performance (last 20 trades)
    - Reduces risk by 50% when win rate < 50%
    - Increases risk by 25% when win rate > 70%
    - Caps minimum risk at 0.5%
    - Caps maximum risk at 3%
    - Adjusts position sizes based on current market volatility (ATR)
    - Calculates volatility multiplier: size *= (1 / volatility_ratio)
    - Applies minimum multiplier of 0.3 (for V100 high volatility)
    - Applies maximum multiplier of 1.5 (for V10 low volatility)
    - Logs all risk adjustments with reasoning
    - Stores risk adjustment history in database
    - Stores volatility adjustments in database

    Usage:
        risk_manager = AdaptiveRiskManager(
            performance_comparator=comparator,
            database_path="adaptive_risk.db"
        )

        # Get current risk percentage
        risk_pct = risk_manager.calculate_base_risk()

        # Adjust risk based on recent performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Calculate position size for a trade with volatility adjustment
        position_size = risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=1.0850,
            stop_loss=1.0800,
            symbol="EURUSD"
        )

        # Get volatility multiplier for a symbol
        vol_mult = risk_manager.calculate_volatility_multiplier("EURUSD")
    """

    def __init__(
        self,
        performance_comparator: PerformanceComparator,
        database_path: str = "adaptive_risk.db",
        base_risk_percent: float = 2.0,
        min_risk_percent: float = 0.5,
        max_risk_percent: float = 3.0,
        performance_window: int = 20,
        atr_period: int = 14,
        atr_lookback: int = 100,
        min_volatility_multiplier: float = 0.3,
        max_volatility_multiplier: float = 1.5,
        enable_volatility_adjustment: bool = True,
        drawdown_threshold_1: float = 10.0,
        drawdown_threshold_2: float = 15.0,
        drawdown_threshold_3: float = 20.0,
        initial_account_balance: float = 10000.0,
        hourly_risk_multipliers: Optional[dict[int, float]] = None,
        enable_session_adjustment: bool = True,
        min_stop_distance_pct: float = 0.5,
        max_stop_distance_pct: float = 2.0,
        low_volatility_atr_multiplier: float = 1.5,
        high_volatility_atr_multiplier: float = 3.0,
        min_tp_atr_multiplier: float = 1.0,
        max_tp_atr_multiplier: float = 5.0,
        high_win_rate_tp_multiplier: float = 2.0,
        low_win_rate_tp_multiplier: float = 3.0,
        win_rate_threshold: float = 60.0,
    ):
        """
        Initialize the AdaptiveRiskManager.

        Args:
            performance_comparator: PerformanceComparator for accessing trade history
            database_path: Path to SQLite database for storing risk adjustments
            base_risk_percent: Default base risk percentage (default: 2.0%)
            min_risk_percent: Minimum allowed risk percentage (default: 0.5%)
            max_risk_percent: Maximum allowed risk percentage (default: 3.0%)
            performance_window: Number of recent trades to analyze (default: 20)
            atr_period: Period for ATR calculation (default: 14)
            atr_lookback: Number of bars to calculate average ATR (default: 100)
            min_volatility_multiplier: Minimum volatility multiplier for high volatility (default: 0.3)
            max_volatility_multiplier: Maximum volatility multiplier for low volatility (default: 1.5)
            enable_volatility_adjustment: Whether to enable volatility-based position sizing (default: True)
            drawdown_threshold_1: First drawdown threshold for risk reduction (default: 10.0%)
            drawdown_threshold_2: Second drawdown threshold for risk reduction (default: 15.0%)
            drawdown_threshold_3: Circuit breaker drawdown threshold (default: 20.0%)
            initial_account_balance: Starting account balance for equity curve tracking (default: 10000.0)
            hourly_risk_multipliers: Dict mapping hour (0-23) to risk multiplier (default: None)
            enable_session_adjustment: Whether to enable time-based session risk adjustment (default: True)
            min_stop_distance_pct: Minimum stop distance as percentage of price (default: 0.5%)
            max_stop_distance_pct: Maximum stop distance as percentage of price (default: 2.0%)
            low_volatility_atr_multiplier: ATR multiplier for low volatility stops (default: 1.5)
            high_volatility_atr_multiplier: ATR multiplier for high volatility stops (default: 3.0)
            min_tp_atr_multiplier: Minimum TP multiplier as ATR multiple (default: 1.0)
            max_tp_atr_multiplier: Maximum TP multiplier as ATR multiple (default: 5.0)
            high_win_rate_tp_multiplier: TP multiplier when win rate > threshold (default: 2.0)
            low_win_rate_tp_multiplier: TP multiplier when win rate <= threshold (default: 3.0)
            win_rate_threshold: Win rate threshold for TP adjustment (default: 60.0%)
        """
        self._performance_comparator = performance_comparator
        self._database_path = database_path
        self._base_risk_percent = base_risk_percent
        self._min_risk_percent = min_risk_percent
        self._max_risk_percent = max_risk_percent
        self._performance_window = performance_window
        self._atr_period = atr_period
        self._atr_lookback = atr_lookback
        self._min_volatility_multiplier = min_volatility_multiplier
        self._max_volatility_multiplier = max_volatility_multiplier
        self._enable_volatility_adjustment = enable_volatility_adjustment
        self._drawdown_threshold_1 = drawdown_threshold_1
        self._drawdown_threshold_2 = drawdown_threshold_2
        self._drawdown_threshold_3 = drawdown_threshold_3
        self._connection: Optional[sqlite3.Connection] = None
        self._adjustment_history: list[RiskAdjustment] = []
        self._volatility_adjustments: list[VolatilityAdjustment] = []
        self._drawdown_adjustments: list[DrawdownAdjustment] = []
        self._correlation_adjustments: list[CorrelationAdjustment] = []
        self._current_risk_percent = base_risk_percent
        self._price_data_cache: dict[str, pd.DataFrame] = {}
        self._initial_account_balance = initial_account_balance
        self._peak_equity = initial_account_balance
        self._trading_halted = False
        self._correlation_threshold: float = 0.7
        self._correlation_lookback: int = 100
        self._correlation_reduction_per_position: float = 0.2

        # Time-based session risk adjustment
        self._enable_session_adjustment = enable_session_adjustment
        self._hourly_risk_multipliers = hourly_risk_multipliers or self._get_default_hourly_multipliers()
        self._session_risk_adjustments: list[SessionRiskAdjustment] = []

        # Dynamic stop loss parameters
        self._min_stop_distance_pct = min_stop_distance_pct
        self._max_stop_distance_pct = max_stop_distance_pct
        self._low_volatility_atr_multiplier = low_volatility_atr_multiplier
        self._high_volatility_atr_multiplier = high_volatility_atr_multiplier
        self._dynamic_stop_adjustments: list[DynamicStopAdjustment] = []

        # Profit target optimization parameters
        self._min_tp_atr_multiplier = min_tp_atr_multiplier
        self._max_tp_atr_multiplier = max_tp_atr_multiplier
        self._high_win_rate_tp_multiplier = high_win_rate_tp_multiplier
        self._low_win_rate_tp_multiplier = low_win_rate_tp_multiplier
        self._win_rate_threshold = win_rate_threshold
        self._profit_target_adjustments: list[ProfitTargetAdjustment] = []

        # Initialize database
        self._initialize_database()

        # Load latest risk settings from database
        self._load_latest_risk_settings()

        logger.info(
            f"AdaptiveRiskManager initialized: base_risk={base_risk_percent}%, "
            f"min_risk={min_risk_percent}%, max_risk={max_risk_percent}%, "
            f"window={performance_window} trades, "
            f"volatility_adjustment={enable_volatility_adjustment}, "
            f"drawdown_thresholds=[{drawdown_threshold_1}%, {drawdown_threshold_2}%, {drawdown_threshold_3}%]"
        )

    def _initialize_database(self) -> None:
        """
        Initialize the SQLite database with required tables.

        Creates tables for:
        - risk_adjustments: Risk adjustment history
        - risk_settings: Current risk settings snapshots
        - volatility_adjustments: Volatility-based position sizing history
        - drawdown_adjustments: Drawdown-based risk adjustment history
        """
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create risk_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    old_risk_percent REAL NOT NULL,
                    new_risk_percent REAL NOT NULL,
                    adjustment_type TEXT NOT NULL,
                    win_rate REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create risk_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    base_risk_percent REAL NOT NULL,
                    min_risk_percent REAL NOT NULL,
                    max_risk_percent REAL NOT NULL,
                    current_risk_percent REAL NOT NULL,
                    performance_window INTEGER NOT NULL,
                    last_updated TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create volatility_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS volatility_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    current_atr REAL NOT NULL,
                    average_atr REAL NOT NULL,
                    volatility_ratio REAL NOT NULL,
                    volatility_multiplier REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create drawdown_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drawdown_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    old_risk_percent REAL NOT NULL,
                    new_risk_percent REAL NOT NULL,
                    current_drawdown REAL NOT NULL,
                    peak_equity REAL NOT NULL,
                    current_equity REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create correlation_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS correlation_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    correlated_symbols TEXT NOT NULL,
                    correlation_count INTEGER NOT NULL,
                    adjustment_multiplier REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create session_risk_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_risk_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    risk_multiplier REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create dynamic_stop_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dynamic_stop_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    direction TEXT NOT NULL,
                    current_atr REAL NOT NULL,
                    atr_multiplier REAL NOT NULL,
                    volatility_regime TEXT NOT NULL,
                    calculated_stop REAL NOT NULL,
                    stop_distance_pct REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create profit_target_adjustments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profit_target_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    direction TEXT NOT NULL,
                    current_atr REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    atr_multiplier REAL NOT NULL,
                    calculated_tp REAL NOT NULL,
                    tp_distance_pct REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create tp_hit_tracking table for tracking TP hit rate
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tp_hit_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    direction TEXT NOT NULL,
                    tp_price REAL NOT NULL,
                    atr_multiplier REAL NOT NULL,
                    tp_hit BOOLEAN NOT NULL,
                    exit_price REAL,
                    holding_time_hours REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adjustments_timestamp
                ON risk_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_updated
                ON risk_settings(last_updated DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_volatility_timestamp
                ON volatility_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_volatility_symbol
                ON volatility_adjustments(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_drawdown_timestamp
                ON drawdown_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_correlation_timestamp
                ON correlation_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_correlation_symbol
                ON correlation_adjustments(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_timestamp
                ON session_risk_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_hour
                ON session_risk_adjustments(hour)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_dynamic_stop_timestamp
                ON dynamic_stop_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_dynamic_stop_symbol
                ON dynamic_stop_adjustments(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_profit_target_timestamp
                ON profit_target_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_profit_target_symbol
                ON profit_target_adjustments(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tp_hit_timestamp
                ON tp_hit_tracking(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tp_hit_symbol
                ON tp_hit_tracking(symbol)
            """)

            self._connection.commit()

            logger.info("Adaptive risk database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_latest_risk_settings(self) -> None:
        """
        Load the latest risk settings from the database.

        If no settings exist in the database, uses initialization values.
        """
        if self._connection is None:
            logger.warning("Database connection not available, using default risk settings")
            return

        try:
            cursor = self._connection.cursor()

            # Get the most recent risk settings
            cursor.execute("""
                SELECT base_risk_percent, min_risk_percent, max_risk_percent,
                       current_risk_percent, performance_window, last_updated
                FROM risk_settings
                ORDER BY created_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()

            if row:
                self._base_risk_percent = row[0]
                self._min_risk_percent = row[1]
                self._max_risk_percent = row[2]
                self._current_risk_percent = row[3]
                self._performance_window = row[4]

                logger.info(
                    f"Loaded latest risk settings from {row[5]}: "
                    f"current_risk={self._current_risk_percent:.2f}%"
                )
            else:
                logger.info("No saved risk settings found, using initialization values")

        except sqlite3.Error as e:
            logger.error(f"Failed to load risk settings from database: {e}")

    def calculate_base_risk(self) -> float:
        """
        Calculate the base risk percentage.

        Returns:
            Base risk percentage (default: 2.0%)
        """
        return self._base_risk_percent

    def _get_recent_trade_outcomes(self) -> list[TradeOutcome]:
        """
        Get recent trade outcomes for performance analysis.

        Returns:
            List of recent TradeOutcome objects (limited by performance_window)
        """
        # Get recent outcomes from performance comparator
        recent_outcomes = self._performance_comparator.get_trade_outcomes(
            limit=self._performance_window
        )

        logger.debug(f"Retrieved {len(recent_outcomes)} recent trade outcomes for risk analysis")

        return recent_outcomes

    def _calculate_win_rate(self, outcomes: list[TradeOutcome]) -> float:
        """
        Calculate win rate from trade outcomes.

        Args:
            outcomes: List of TradeOutcome objects

        Returns:
            Win rate percentage (0-100)
        """
        if not outcomes:
            # No trades yet, use neutral win rate
            return 50.0

        winning_trades = sum(1 for o in outcomes if o.final_profit > 0)
        win_rate = (winning_trades / len(outcomes)) * 100

        logger.debug(f"Calculated win rate: {win_rate:.2f}% ({winning_trades}/{len(outcomes)} wins)")

        return win_rate

    def adjust_for_recent_performance(self) -> float:
        """
        Adjust risk based on recent trading performance.

        Risk adjustment rules:
        - Reduce risk by 50% when win rate < 50% (last 20 trades)
        - Increase risk by 25% when win rate > 70% (last 20 trades)
        - Keep base risk when win rate is between 50% and 70%
        - Always cap between min_risk_percent and max_risk_percent

        Returns:
            Adjusted risk percentage
        """
        # Get recent trade outcomes
        recent_outcomes = self._get_recent_trade_outcomes()

        # Calculate win rate
        win_rate = self._calculate_win_rate(recent_outcomes)

        # Calculate adjusted risk
        old_risk = self._current_risk_percent
        new_risk = self._base_risk_percent

        if win_rate < 50.0:
            # Reduce risk by 50% when win rate is below 50%
            new_risk = self._base_risk_percent * 0.5
            adjustment_type = "performance_decrease"
            reason = (
                f"Win rate ({win_rate:.1f}%) below 50% threshold. "
                f"Reducing risk by 50% to protect capital during losing streak."
            )
        elif win_rate > 70.0:
            # Increase risk by 25% when win rate is above 70%
            new_risk = self._base_risk_percent * 1.25
            adjustment_type = "performance_increase"
            reason = (
                f"Win rate ({win_rate:.1f}%) above 70% threshold. "
                f"Increasing risk by 25% to maximize winning streak."
            )
        else:
            # Win rate in normal range, use base risk
            new_risk = self._base_risk_percent
            adjustment_type = "performance_normal"
            reason = (
                f"Win rate ({win_rate:.1f}%) in normal range (50-70%). "
                f"Using base risk percentage."
            )

        # Apply min/max caps
        if new_risk < self._min_risk_percent:
            new_risk = self._min_risk_percent
            reason += f" Cap at minimum {self._min_risk_percent}%."
        elif new_risk > self._max_risk_percent:
            new_risk = self._max_risk_percent
            reason += f" Cap at maximum {self._max_risk_percent}%."

        # Create adjustment record
        adjustment = RiskAdjustment(
            timestamp=datetime.utcnow(),
            old_risk_percent=old_risk,
            new_risk_percent=new_risk,
            adjustment_type=adjustment_type,
            win_rate=win_rate,
            reason=reason,
        )

        # Store adjustment in history
        self._adjustment_history.append(adjustment)

        # Update current risk
        self._current_risk_percent = new_risk

        # Store in database
        self._store_risk_adjustment(adjustment)
        self._store_risk_settings()

        # Log the adjustment
        logger.info(
            f"Risk adjusted based on performance: {old_risk:.2f}% -> {new_risk:.2f}% | "
            f"Win rate: {win_rate:.1f}% | Reason: {reason}"
        )

        return new_risk

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        direction: str = "BUY",
        symbol: str = "EURUSD",
    ) -> float:
        """
        Calculate position size based on current risk percentage and volatility.

        Args:
            account_balance: Current account balance
            entry_price: Entry price for the trade
            stop_loss: Stop loss price for the trade
            direction: "BUY" or "SELL" (default: "BUY")
            symbol: Trading symbol (default: "EURUSD")

        Returns:
            Position size in lots
        """
        # Calculate risk amount in currency
        risk_amount = account_balance * (self._current_risk_percent / 100)

        # Calculate risk per lot (in price difference)
        if direction.upper() == "BUY":
            risk_per_lot_price = abs(entry_price - stop_loss)
        else:  # SELL
            risk_per_lot_price = abs(stop_loss - entry_price)

        # Avoid division by zero
        if risk_per_lot_price == 0:
            logger.warning(
                f"Risk per lot is zero (entry={entry_price}, sl={stop_loss}). "
                f"Cannot calculate position size."
            )
            return 0.0

        # For forex, 1 standard lot = 100,000 units
        lot_multiplier = 100000

        # Calculate base position size in lots
        base_position_size = risk_amount / (risk_per_lot_price * lot_multiplier)

        # Apply adjustments in sequence: volatility -> session
        adjusted_position_size = base_position_size

        # Apply volatility adjustment if enabled
        if self._enable_volatility_adjustment:
            volatility_multiplier = self.calculate_volatility_multiplier(symbol)
            adjusted_position_size *= volatility_multiplier

        # Apply session-based time adjustment if enabled
        if self._enable_session_adjustment:
            session_multiplier = self.calculate_session_risk_multiplier()
            adjusted_position_size *= session_multiplier

        logger.debug(
            f"Position size calculation: balance={account_balance:.2f}, "
            f"risk_pct={self._current_risk_percent:.2f}%, "
            f"risk_amount={risk_amount:.2f}, "
            f"risk_per_lot={risk_per_lot_price:.5f}, "
            f"base_position_size={base_position_size:.2f} lots, "
            f"volatility_adjustment={self._enable_volatility_adjustment}, "
            f"session_adjustment={self._enable_session_adjustment}, "
            f"final_position_size={adjusted_position_size:.2f} lots"
        )

        return adjusted_position_size

    def get_current_risk_percent(self) -> float:
        """
        Get the current risk percentage.

        Returns:
            Current risk percentage
        """
        return self._current_risk_percent

    def calculate_volatility_multiplier(self, symbol: str) -> float:
        """
        Calculate volatility-based position size multiplier for a symbol.

        Uses ATR (Average True Range) to measure current volatility relative to
        historical average and adjusts position size accordingly.

        Formula:
            volatility_ratio = current_ATR / average_ATR
            volatility_multiplier = 1 / volatility_ratio
            volatility_multiplier = clamp(volatility_multiplier, min, max)

        Where:
            - current_ATR: Most recent ATR value
            - average_ATR: Average ATR over lookback period (default: 100 bars)
            - min: 0.3 (for high volatility symbols like V100)
            - max: 1.5 (for low volatility symbols like V10)

        Args:
            symbol: Trading symbol (e.g., "EURUSD", "GBPUSD", "V10", "V100")

        Returns:
            Volatility multiplier (0.3 to 1.5)
        """
        try:
            # Fetch price data for ATR calculation
            price_data = self._fetch_price_data(symbol)

            if price_data is None or len(price_data) < self._atr_lookback:
                logger.warning(
                    f"Insufficient price data for {symbol} (need {self._atr_lookback} bars). "
                    f"Using default volatility multiplier of 1.0"
                )
                return 1.0

            # Calculate ATR values
            atr_values = self._calculate_atr(price_data, self._atr_period)

            if len(atr_values) < self._atr_lookback:
                logger.warning(
                    f"Insufficient ATR values for {symbol} (need {self._atr_lookback}, have {len(atr_values)}). "
                    f"Using default volatility multiplier of 1.0"
                )
                return 1.0

            # Get current ATR (most recent)
            current_atr = atr_values.iloc[-1]

            # Calculate average ATR over lookback period
            average_atr = atr_values.iloc[-self._atr_lookback:].mean()

            # Calculate volatility ratio
            volatility_ratio = current_atr / average_atr if average_atr > 0 else 1.0

            # Calculate volatility multiplier: inverse of volatility ratio
            # High volatility (ratio > 1) = reduce position size (multiplier < 1)
            # Low volatility (ratio < 1) = increase position size (multiplier > 1)
            volatility_multiplier = 1.0 / volatility_ratio

            # Apply min/max bounds
            volatility_multiplier = max(
                self._min_volatility_multiplier,
                min(self._max_volatility_multiplier, volatility_multiplier)
            )

            # Generate reason
            if volatility_ratio > 1.3:
                reason = (
                    f"High volatility detected: current ATR ({current_atr:.6f}) is "
                    f"{volatility_ratio:.2f}x higher than average ({average_atr:.6f}). "
                    f"Reducing position size to {volatility_multiplier:.2f}x to manage risk."
                )
            elif volatility_ratio > 1.1:
                reason = (
                    f"Moderately high volatility: current ATR ({current_atr:.6f}) is "
                    f"{volatility_ratio:.2f}x higher than average ({average_atr:.6f}). "
                    f"Slightly reducing position size to {volatility_multiplier:.2f}x."
                )
            elif volatility_ratio < 0.7:
                reason = (
                    f"Low volatility detected: current ATR ({current_atr:.6f}) is "
                    f"{volatility_ratio:.2f}x lower than average ({average_atr:.6f}). "
                    f"Increasing position size to {volatility_multiplier:.2f}x to capitalize on stability."
                )
            elif volatility_ratio < 0.9:
                reason = (
                    f"Moderately low volatility: current ATR ({current_atr:.6f}) is "
                    f"{volatility_ratio:.2f}x lower than average ({average_atr:.6f}). "
                    f"Slightly increasing position size to {volatility_multiplier:.2f}x."
                )
            else:
                reason = (
                    f"Normal volatility: current ATR ({current_atr:.6f}) is "
                    f"{volatility_ratio:.2f}x of average ({average_atr:.6f}). "
                    f"Using standard position size multiplier of {volatility_multiplier:.2f}x."
                )

            # Create and store volatility adjustment record
            adjustment = VolatilityAdjustment(
                timestamp=datetime.utcnow(),
                symbol=symbol,
                current_atr=float(current_atr),
                average_atr=float(average_atr),
                volatility_ratio=float(volatility_ratio),
                volatility_multiplier=float(volatility_multiplier),
                reason=reason,
            )

            self._volatility_adjustments.append(adjustment)
            self._store_volatility_adjustment(adjustment)

            # Log the adjustment
            logger.info(
                f"Volatility multiplier calculated for {symbol}: {volatility_multiplier:.3f} "
                f"| Current ATR: {current_atr:.6f} | Avg ATR: {average_atr:.6f} "
                f"| Ratio: {volatility_ratio:.3f}"
            )

            return float(volatility_multiplier)

        except Exception as e:
            logger.error(f"Error calculating volatility multiplier for {symbol}: {e}")
            return 1.0

    def _fetch_price_data(self, symbol: str, timeframe: str = "H1") -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for a symbol.

        In production, this would fetch from MT5 or a market data provider.
        For now, generates synthetic data for testing.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for bars (default: "H1")

        Returns:
            DataFrame with 'high', 'low', 'close' columns, or None if unavailable
        """
        # Check cache first
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self._price_data_cache:
            cached_data = self._price_data_cache[cache_key]
            if len(cached_data) >= self._atr_lookback:
                logger.debug(f"Using cached price data for {symbol}")
                return cached_data

        try:
            # TODO: Replace with actual MT5 API call
            # For now, generate synthetic data for testing
            logger.warning(
                f"Using synthetic price data for {symbol}. "
                f"Replace with actual MT5 data fetching in production."
            )

            # Generate synthetic price data
            np.random.seed(hash(symbol) % 2**32)  # Consistent data per symbol
            num_bars = self._atr_lookback + 50

            # Base price depends on symbol
            if "V10" in symbol or "V100" in symbol:
                # Indices/volatility symbols
                base_price = 100.0 if "V100" in symbol else 10.0
                volatility_factor = 0.02 if "V100" in symbol else 0.005
            else:
                # Forex pairs
                base_price = 1.1000  # EURUSD-like
                volatility_factor = 0.002

            # Generate price series
            price_changes = np.random.normal(0, volatility_factor, num_bars)
            close_prices = base_price * (1 + price_changes).cumprod()

            # Generate high/low from close
            high_prices = close_prices * (1 + np.abs(np.random.normal(0, volatility_factor/2, num_bars)))
            low_prices = close_prices * (1 - np.abs(np.random.normal(0, volatility_factor/2, num_bars)))

            # Create DataFrame
            data = pd.DataFrame({
                'high': high_prices,
                'low': low_prices,
                'close': close_prices,
            })

            # Cache the data
            self._price_data_cache[cache_key] = data

            logger.debug(f"Generated {len(data)} bars of synthetic price data for {symbol}")

            return data

        except Exception as e:
            logger.error(f"Failed to fetch price data for {symbol}: {e}")
            return None

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR) for price data.

        ATR measures market volatility by taking the average of true ranges
        over a specified period.

        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))

        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            period: ATR period (default: 14)

        Returns:
            Series of ATR values
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']

            # Calculate previous close
            prev_close = close.shift(1)

            # Calculate True Range components
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()

            # True Range is the maximum of the three
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Calculate ATR using exponential moving average (Wilder's smoothing)
            atr = true_range.ewm(alpha=1/period, adjust=False).mean()

            logger.debug(f"Calculated ATR with period {period}: {len(atr)} values")

            return atr

        except Exception as e:
            logger.error(f"Failed to calculate ATR: {e}")
            return pd.Series()

    def _store_volatility_adjustment(self, adjustment: VolatilityAdjustment) -> None:
        """
        Store a volatility adjustment in the database.

        Args:
            adjustment: VolatilityAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO volatility_adjustments (
                    timestamp, symbol, current_atr, average_atr,
                    volatility_ratio, volatility_multiplier, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.symbol,
                adjustment.current_atr,
                adjustment.average_atr,
                adjustment.volatility_ratio,
                adjustment.volatility_multiplier,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Volatility adjustment stored in database for {adjustment.symbol}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store volatility adjustment in database: {e}")

    def get_volatility_adjustments(self, symbol: Optional[str] = None, limit: int = 100) -> list[VolatilityAdjustment]:
        """
        Get volatility adjustment history.

        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of adjustments to return

        Returns:
            List of VolatilityAdjustment records
        """
        if symbol is None:
            return self._volatility_adjustments[-limit:]
        return [v for v in self._volatility_adjustments if v.symbol == symbol][-limit:]

    def calculate_drawdown(self, current_equity: float) -> tuple[float, float, float]:
        """
        Calculate current drawdown from equity curve.

        Drawdown is calculated as the percentage decline from the peak equity.
        This method tracks the peak equity and calculates the current drawdown
        based on the provided current equity value.

        Formula:
            drawdown_percent = ((peak_equity - current_equity) / peak_equity) * 100

        Args:
            current_equity: Current account equity value

        Returns:
            Tuple of (drawdown_percent, peak_equity, current_equity)
        """
        # Update peak equity if current equity is higher
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
            logger.info(f"New peak equity established: {self._peak_equity:.2f}")

        # Calculate drawdown percentage
        if self._peak_equity > 0:
            drawdown_percent = ((self._peak_equity - current_equity) / self._peak_equity) * 100
        else:
            drawdown_percent = 0.0

        # Log drawdown if significant
        if drawdown_percent > 5.0:
            logger.warning(
                f"Current drawdown: {drawdown_percent:.2f}% | "
                f"Peak: {self._peak_equity:.2f} | Current: {current_equity:.2f}"
            )

        return drawdown_percent, self._peak_equity, current_equity

    def adjust_for_drawdown(self, current_equity: float) -> tuple[float, bool]:
        """
        Adjust risk based on current drawdown from equity peak.

        Drawdown-based risk reduction rules:
        - Reduce risk by 50% when drawdown > 10% (threshold_1)
        - Reduce risk by 75% when drawdown > 15% (threshold_2)
        - Stop trading entirely when drawdown > 20% (threshold_3) - circuit breaker
        - Gradually restore risk as drawdown recovers

        This method implements a circuit breaker pattern to protect capital
        during significant drawdowns and allows for gradual risk recovery
        as the account equity recovers.

        Args:
            current_equity: Current account equity value

        Returns:
            Tuple of (adjusted_risk_percent, trading_allowed)
            - adjusted_risk_percent: New risk percentage (or 0 if trading halted)
            - trading_allowed: False if circuit breaker triggered, True otherwise
        """
        # Calculate current drawdown
        drawdown_percent, peak_equity, equity = self.calculate_drawdown(current_equity)

        old_risk = self._current_risk_percent
        new_risk = old_risk
        trading_allowed = True
        reason = ""

        # Check if trading should be halted (circuit breaker)
        if drawdown_percent >= self._drawdown_threshold_3:
            # Circuit breaker: stop trading entirely
            new_risk = 0.0
            trading_allowed = False
            self._trading_halted = True
            reason = (
                f"CIRCUIT BREAKER TRIGGERED: Drawdown ({drawdown_percent:.2f}%) exceeds "
                f"maximum threshold ({self._drawdown_threshold_3:.1f}%). "
                f"Trading halted to protect remaining capital. "
                f"Peak equity: {peak_equity:.2f}, Current equity: {equity:.2f}."
            )
            logger.critical(reason)

        # Check if trading is already halted
        elif self._trading_halted:
            # Trading is halted - check if drawdown has recovered enough to resume
            recovery_threshold = self._drawdown_threshold_2  # Resume trading when below 15%
            if drawdown_percent < recovery_threshold:
                # Resume trading with reduced risk
                self._trading_halted = False
                new_risk = self._base_risk_percent * 0.5  # Start with 50% of base risk
                reason = (
                    f"CIRCUIT BREAKER LIFTED: Drawdown recovered to {drawdown_percent:.2f}% "
                    f"(below recovery threshold of {recovery_threshold:.1f}%). "
                    f"Resuming trading with reduced risk ({new_risk:.2f}%). "
                    f"Peak equity: {peak_equity:.2f}, Current equity: {equity:.2f}."
                )
                logger.info(reason)
            else:
                # Still in circuit breaker mode
                new_risk = 0.0
                trading_allowed = False
                reason = (
                    f"Still in circuit breaker mode: Drawdown ({drawdown_percent:.2f}%) "
                    f"has not recovered below recovery threshold ({recovery_threshold:.1f}%). "
                    f"Trading remains halted."
                )
                logger.warning(reason)

        # Check for second level drawdown reduction (75% reduction)
        elif drawdown_percent >= self._drawdown_threshold_2:
            # Reduce risk by 75%
            new_risk = self._base_risk_percent * 0.25
            new_risk = max(new_risk, self._min_risk_percent)
            reason = (
                f"SEVERE DRAWDOWN: Drawdown ({drawdown_percent:.2f}%) exceeds "
                f"threshold 2 ({self._drawdown_threshold_2:.1f}%). "
                f"Reducing risk by 75% to {new_risk:.2f}% to preserve capital. "
                f"Peak equity: {peak_equity:.2f}, Current equity: {equity:.2f}."
            )
            logger.warning(reason)

        # Check for first level drawdown reduction (50% reduction)
        elif drawdown_percent >= self._drawdown_threshold_1:
            # Reduce risk by 50%
            new_risk = self._base_risk_percent * 0.5
            new_risk = max(new_risk, self._min_risk_percent)
            reason = (
                f"MODERATE DRAWDOWN: Drawdown ({drawdown_percent:.2f}%) exceeds "
                f"threshold 1 ({self._drawdown_threshold_1:.1f}%). "
                f"Reducing risk by 50% to {new_risk:.2f}%. "
                f"Peak equity: {peak_equity:.2f}, Current equity: {equity:.2f}."
            )
            logger.warning(reason)

        # Gradual risk restoration as drawdown recovers
        else:
            # Drawdown is below first threshold
            # Gradually restore risk based on recovery progress
            recovery_ratio = drawdown_percent / self._drawdown_threshold_1
            # Risk scales from 50% at 10% DD to 100% at 0% DD
            risk_multiplier = 0.5 + (0.5 * (1.0 - recovery_ratio))
            new_risk = self._base_risk_percent * risk_multiplier

            # Only log if risk is being restored
            if new_risk > old_risk:
                reason = (
                    f"DRAWDOWN RECOVERY: Drawdown ({drawdown_percent:.2f}%) recovering. "
                    f"Gradually restoring risk to {new_risk:.2f}% "
                    f"({risk_multiplier*100:.1f}% of base risk). "
                    f"Peak equity: {peak_equity:.2f}, Current equity: {equity:.2f}."
                )
                logger.info(reason)
            else:
                # No adjustment needed - use current risk
                new_risk = old_risk
                reason = (
                    f"DRAWDOWN NORMAL: Drawdown ({drawdown_percent:.2f}%) is within acceptable range. "
                    f"Maintaining current risk level of {new_risk:.2f}%. "
                    f"Peak equity: {peak_equity:.2f}, Current equity: {equity:.2f}."
                )

        # Create adjustment record if risk changed
        if abs(new_risk - old_risk) > 0.01:  # Only record significant changes
            adjustment = DrawdownAdjustment(
                timestamp=datetime.utcnow(),
                old_risk_percent=old_risk,
                new_risk_percent=new_risk,
                current_drawdown=drawdown_percent,
                peak_equity=peak_equity,
                current_equity=equity,
                reason=reason,
            )

            # Store adjustment in history
            self._drawdown_adjustments.append(adjustment)

            # Store in database
            self._store_drawdown_adjustment(adjustment)

            # Update current risk
            self._current_risk_percent = new_risk

            # Store risk settings
            self._store_risk_settings()

            # Log the adjustment
            logger.info(
                f"Drawdown-based risk adjustment: {old_risk:.2f}% -> {new_risk:.2f}% | "
                f"Drawdown: {drawdown_percent:.2f}% | Trading allowed: {trading_allowed}"
            )

        return new_risk, trading_allowed

    def is_trading_allowed(self) -> bool:
        """
        Check if trading is currently allowed (circuit breaker status).

        Returns:
            True if trading is allowed, False if circuit breaker is triggered
        """
        return not self._trading_halted

    def reset_circuit_breaker(self) -> None:
        """
        Manually reset the circuit breaker and allow trading.

        This should only be used in exceptional circumstances and with
        proper risk assessment. Use with caution.
        """
        was_halted = self._trading_halted
        self._trading_halted = False
        self._current_risk_percent = self._base_risk_percent * 0.5  # Start with 50% risk

        if was_halted:
            logger.warning(
                f"Circuit breaker manually reset. Trading resumed with reduced risk: "
                f"{self._current_risk_percent:.2f}%"
            )
        else:
            logger.info("Circuit breaker was not active. No reset needed.")

    def get_drawdown_adjustments(self, limit: int = 100) -> list[DrawdownAdjustment]:
        """
        Get drawdown adjustment history.

        Args:
            limit: Maximum number of adjustments to return

        Returns:
            List of DrawdownAdjustment records
        """
        return self._drawdown_adjustments[-limit:]

    def _store_drawdown_adjustment(self, adjustment: DrawdownAdjustment) -> None:
        """
        Store a drawdown adjustment in the database.

        Args:
            adjustment: DrawdownAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO drawdown_adjustments (
                    timestamp, old_risk_percent, new_risk_percent,
                    current_drawdown, peak_equity, current_equity, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.old_risk_percent,
                adjustment.new_risk_percent,
                adjustment.current_drawdown,
                adjustment.peak_equity,
                adjustment.current_equity,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Drawdown adjustment stored in database at {adjustment.timestamp}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store drawdown adjustment in database: {e}")

    def _store_risk_adjustment(self, adjustment: RiskAdjustment) -> None:
        """
        Store a risk adjustment in the database.

        Args:
            adjustment: RiskAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO risk_adjustments (
                    timestamp, old_risk_percent, new_risk_percent,
                    adjustment_type, win_rate, reason
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.old_risk_percent,
                adjustment.new_risk_percent,
                adjustment.adjustment_type,
                adjustment.win_rate,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Risk adjustment stored in database at {adjustment.timestamp}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store risk adjustment in database: {e}")

    def _store_risk_settings(self) -> None:
        """
        Store current risk settings snapshot in database.
        """
        if self._connection is None:
            logger.warning("Database connection not available, settings not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO risk_settings (
                    base_risk_percent, min_risk_percent, max_risk_percent,
                    current_risk_percent, performance_window, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self._base_risk_percent,
                self._min_risk_percent,
                self._max_risk_percent,
                self._current_risk_percent,
                self._performance_window,
                datetime.utcnow().isoformat(),
            ))

            self._connection.commit()

            logger.debug("Risk settings snapshot stored in database")

        except sqlite3.Error as e:
            logger.error(f"Failed to store risk settings in database: {e}")

    def get_adjustment_history(self, limit: int = 100) -> list[RiskAdjustment]:
        """
        Get risk adjustment history.

        Args:
            limit: Maximum number of adjustments to return

        Returns:
            List of RiskAdjustment records
        """
        return self._adjustment_history[-limit:]

    def reset_to_base_risk(self) -> float:
        """
        Reset risk to base percentage.

        Returns:
            Base risk percentage
        """
        old_risk = self._current_risk_percent
        self._current_risk_percent = self._base_risk_percent

        logger.info(f"Risk reset to base: {old_risk:.2f}% -> {self._base_risk_percent:.2f}%")

        return self._current_risk_percent

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        self.close()

    def calculate_portfolio_correlation(
        self,
        target_symbol: str,
        open_positions: list[TradePosition]
    ) -> tuple[float, list[str], int]:
        """
        Calculate correlation-based risk adjustment for a potential new position.

        This method analyzes the correlation between the target symbol and all
        currently open positions. It reduces position size when there are multiple
        positions in highly correlated symbols (correlation > 0.7).

        Args:
            target_symbol: Symbol for which to calculate correlation adjustment
            open_positions: List of currently open positions

        Returns:
            Tuple of (adjustment_multiplier, correlated_symbols, correlation_count)
            - adjustment_multiplier: Position size multiplier (1.0 = no adjustment)
            - correlated_symbols: List of symbols correlated with target_symbol
            - correlation_count: Number of correlated positions found
        """
        if not open_positions:
            # No open positions, no correlation risk
            logger.debug(f"No open positions, no correlation adjustment needed for {target_symbol}")
            return 1.0, [], 0

        # Get unique symbols from open positions
        open_symbols = list(set(pos.symbol for pos in open_positions))

        # Create list of unique symbols to analyze (target + open positions)
        symbols_to_analyze = list(set([target_symbol] + open_symbols))

        # If we only have one unique symbol (target not in open positions), no correlation analysis needed
        if len(symbols_to_analyze) < 2:
            logger.debug(f"Only one unique symbol to analyze, no correlation adjustment needed for {target_symbol}")
            return 1.0, [], 0

        logger.debug(f"Analyzing correlation for {target_symbol} against {len(open_symbols)} open symbols")

        # Calculate correlation matrix
        correlation_matrix = self._calculate_correlation_matrix(symbols_to_analyze)

        if correlation_matrix is None or correlation_matrix.empty:
            logger.warning(f"Could not calculate correlation matrix for {target_symbol}, using no adjustment")
            return 1.0, [], 0

        # Find symbols highly correlated with target (correlation > 0.7)
        correlated_symbols = []
        target_correlations = correlation_matrix[target_symbol]

        for symbol in open_symbols:
            if symbol in target_correlations:
                correlation = target_correlations[symbol]
                # Check if correlation is significant (can be positive or negative)
                if abs(correlation) > self._correlation_threshold:
                    correlated_symbols.append((symbol, correlation))

        # Sort by absolute correlation (highest first)
        correlated_symbols.sort(key=lambda x: abs(x[1]), reverse=True)

        correlation_count = len(correlated_symbols)
        correlated_symbol_names = [sym for sym, _ in correlated_symbols]

        # Calculate adjustment multiplier
        # First correlated position: no reduction (1.0)
        # Each additional correlated position: 20% reduction
        if correlation_count == 0:
            adjustment_multiplier = 1.0
            reason = (
                f"No significant correlations found for {target_symbol}. "
                f"Using standard position size."
            )
        else:
            # Calculate reduction: 20% for each correlated position beyond the first
            reduction = min(correlation_count - 1, 0) * self._correlation_reduction_per_position
            adjustment_multiplier = max(0.2, 1.0 - reduction)  # Minimum 20% of original size

            correlation_details = ", ".join([
                f"{sym} ({corr:.2f})" for sym, corr in correlated_symbols
            ])
            reason = (
                f"Found {correlation_count} correlated position(s) for {target_symbol}: "
                f"{correlation_details}. "
                f"Applying {adjustment_multiplier:.2f}x position size multiplier "
                f"({(1-adjustment_multiplier)*100:.1f}% reduction)."
            )

        # Create and store adjustment record
        adjustment = CorrelationAdjustment(
            timestamp=datetime.utcnow(),
            symbol=target_symbol,
            correlated_symbols=correlated_symbol_names,
            correlation_count=correlation_count,
            adjustment_multiplier=adjustment_multiplier,
            reason=reason,
        )

        self._correlation_adjustments.append(adjustment)
        self._store_correlation_adjustment(adjustment)

        # Log the adjustment
        logger.info(
            f"Correlation adjustment for {target_symbol}: {adjustment_multiplier:.3f}x | "
            f"Correlated positions: {correlation_count} | "
            f"Symbols: {correlated_symbol_names if correlated_symbol_names else 'None'}"
        )

        return adjustment_multiplier, correlated_symbol_names, correlation_count

    def _calculate_correlation_matrix(self, symbols: list[str]) -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix between symbols using historical price data.

        Uses the last 100 bars of close prices to calculate Pearson correlation
        coefficients between all pairs of symbols.

        Args:
            symbols: List of symbols to analyze

        Returns:
            DataFrame correlation matrix, or None if calculation fails
        """
        if len(symbols) < 2:
            logger.debug("Need at least 2 symbols to calculate correlation matrix")
            return None

        try:
            # Fetch price data for all symbols
            price_data = {}
            for symbol in symbols:
                data = self._fetch_price_data(symbol)
                if data is not None and len(data) >= self._correlation_lookback:
                    # Use last N bars of close prices
                    price_data[symbol] = data['close'].iloc[-self._correlation_lookback:]
                else:
                    logger.warning(f"Insufficient price data for {symbol}")

            if len(price_data) < 2:
                logger.warning("Need price data for at least 2 symbols to calculate correlation")
                return None

            # Create DataFrame with all symbols
            df = pd.DataFrame(price_data)

            # Calculate correlation matrix
            correlation_matrix = df.corr(method='pearson')

            logger.debug(f"Calculated correlation matrix for {len(symbols)} symbols")
            logger.debug(f"Correlation matrix shape: {correlation_matrix.shape}")

            return correlation_matrix

        except Exception as e:
            logger.error(f"Failed to calculate correlation matrix: {e}")
            return None

    def adjust_position_size_for_correlation(
        self,
        base_position_size: float,
        target_symbol: str,
        open_positions: list[TradePosition]
    ) -> float:
        """
        Adjust position size based on portfolio correlation.

        This is a convenience method that combines correlation analysis with
        position size calculation.

        Args:
            base_position_size: Calculated position size before correlation adjustment
            target_symbol: Symbol for the new position
            open_positions: List of currently open positions

        Returns:
            Adjusted position size in lots
        """
        multiplier, correlated_symbols, correlation_count = self.calculate_portfolio_correlation(
            target_symbol=target_symbol,
            open_positions=open_positions
        )

        adjusted_size = base_position_size * multiplier

        logger.info(
            f"Position size adjustment for {target_symbol}: "
            f"{base_position_size:.2f} -> {adjusted_size:.2f} lots "
            f"(multiplier: {multiplier:.3f}, correlated: {correlation_count})"
        )

        return adjusted_size

    def get_correlation_adjustments(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> list[CorrelationAdjustment]:
        """
        Get correlation adjustment history.

        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of adjustments to return

        Returns:
            List of CorrelationAdjustment records
        """
        if symbol is None:
            return self._correlation_adjustments[-limit:]
        return [c for c in self._correlation_adjustments if c.symbol == symbol][-limit:]

    def _store_correlation_adjustment(self, adjustment: CorrelationAdjustment) -> None:
        """
        Store a correlation adjustment in the database.

        Args:
            adjustment: CorrelationAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            # Store correlated symbols as JSON string
            import json
            correlated_symbols_json = json.dumps(adjustment.correlated_symbols)

            cursor.execute("""
                INSERT INTO correlation_adjustments (
                    timestamp, symbol, correlated_symbols,
                    correlation_count, adjustment_multiplier, reason
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.symbol,
                correlated_symbols_json,
                adjustment.correlation_count,
                adjustment.adjustment_multiplier,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Correlation adjustment stored in database for {adjustment.symbol}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store correlation adjustment in database: {e}")

    def _get_default_hourly_multipliers(self) -> dict[int, float]:
        """
        Get default hourly risk multipliers based on trading session patterns.

        Default configuration assumes Forex trading with the following patterns:
        - Asian session (0-8 UTC): Lower volatility and opportunity, reduce risk
        - London open (8-12 UTC): Higher volatility and opportunity, increase risk
        - London/NY overlap (12-16 UTC): Highest volatility, moderate risk
        - NY session (16-21 UTC): Moderate volatility, standard risk
        - Weekend/closed (21-24 UTC): Lower activity, reduce risk

        Returns:
            Dictionary mapping hour (0-23) to risk multiplier
        """
        return {
            # Asian session (00:00 - 08:00 UTC) - Lower risk
            0: 0.6, 1: 0.6, 2: 0.6, 3: 0.6, 4: 0.6, 5: 0.6, 6: 0.6, 7: 0.6,
            # London open (08:00 - 12:00 UTC) - Higher risk
            8: 1.2, 9: 1.2, 10: 1.2, 11: 1.2,
            # London/NY overlap (12:00 - 16:00 UTC) - Moderate-high risk
            12: 1.1, 13: 1.1, 14: 1.1, 15: 1.1,
            # NY session (16:00 - 21:00 UTC) - Standard risk
            16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0,
            # Evening/closed (21:00 - 24:00 UTC) - Lower risk
            21: 0.5, 22: 0.5, 23: 0.5,
        }

    def calculate_session_risk_multiplier(self, current_time: Optional[datetime] = None) -> float:
        """
        Calculate time-based session risk multiplier based on hour of day.

        This method adjusts risk based on trading session patterns. Different
        times of day exhibit different volatility levels and trading opportunities,
        so risk is adjusted accordingly.

        Session patterns (default for Forex):
        - Asian session (0-8 UTC): Lower volatility (0.5x-0.6x multiplier)
        - London open (8-12 UTC): High volatility/opportunity (1.2x multiplier)
        - London/NY overlap (12-16 UTC): High volatility (1.1x multiplier)
        - NY session (16-21 UTC): Standard risk (1.0x multiplier)
        - Evening (21-24 UTC): Low activity (0.5x multiplier)

        Args:
            current_time: Optional datetime for calculation (default: current UTC time)

        Returns:
            Risk multiplier for the current time period (0.5 to 1.2)
        """
        if not self._enable_session_adjustment:
            logger.debug("Session-based risk adjustment is disabled")
            return 1.0

        # Use current time if not provided
        if current_time is None:
            current_time = datetime.utcnow()

        hour = current_time.hour
        day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday

        # Get the multiplier for this hour
        risk_multiplier = self._hourly_risk_multipliers.get(hour, 1.0)

        # Generate reason based on time period
        if 0 <= hour < 8:
            period_name = "Asian session"
            period_description = "lower volatility and trading opportunity"
        elif 8 <= hour < 12:
            period_name = "London open"
            period_description = "higher volatility and opportunity"
        elif 12 <= hour < 16:
            period_name = "London/NY overlap"
            period_description = "high volatility period"
        elif 16 <= hour < 21:
            period_name = "New York session"
            period_description = "standard volatility"
        else:
            period_name = "Evening/weekend"
            period_description = "low activity period"

        # Apply weekend reduction (Saturday/Sunday)
        if day_of_week >= 5:  # Saturday=5, Sunday=6
            risk_multiplier *= 0.5
            period_name += " (weekend)"
            period_description += " with additional weekend reduction"

        # Ensure multiplier doesn't go below minimum
        risk_multiplier = max(0.3, risk_multiplier)

        reason = (
            f"Time-based adjustment: {period_name} (Hour: {hour:02d}:00 UTC, "
            f"Day: {current_time.strftime('%A')}). "
            f"{period_description.capitalize()}. "
            f"Applying {risk_multiplier:.2f}x risk multiplier."
        )

        # Create and store session adjustment record
        adjustment = SessionRiskAdjustment(
            timestamp=current_time,
            hour=hour,
            day_of_week=day_of_week,
            risk_multiplier=risk_multiplier,
            reason=reason,
        )

        self._session_risk_adjustments.append(adjustment)
        self._store_session_risk_adjustment(adjustment)

        # Log the adjustment
        logger.info(
            f"Session risk multiplier: {risk_multiplier:.3f} | "
            f"Hour: {hour:02d}:00 UTC | Day: {current_time.strftime('%A')} | "
            f"Period: {period_name}"
        )

        return risk_multiplier

    def get_session_risk_adjustments(self, limit: int = 100) -> list[SessionRiskAdjustment]:
        """
        Get session risk adjustment history.

        Args:
            limit: Maximum number of adjustments to return

        Returns:
            List of SessionRiskAdjustment records
        """
        return self._session_risk_adjustments[-limit:]

    def _store_session_risk_adjustment(self, adjustment: SessionRiskAdjustment) -> None:
        """
        Store a session risk adjustment in the database.

        Args:
            adjustment: SessionRiskAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO session_risk_adjustments (
                    timestamp, hour, day_of_week, risk_multiplier, reason
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.hour,
                adjustment.day_of_week,
                adjustment.risk_multiplier,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Session risk adjustment stored in database at hour {adjustment.hour}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store session risk adjustment in database: {e}")

    def calculate_dynamic_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
    ) -> tuple[float, float, str]:
        """
        Calculate dynamic stop loss based on current volatility (ATR).

        This method implements dynamic stop loss adjustment that adapts to market
        volatility conditions. Instead of using fixed pip distances, it uses ATR
        (Average True Range) to set appropriate stop distances that account for
        current market noise and volatility.

        Formula:
            stop = entry ± (ATR * multiplier)
            Where multiplier varies based on volatility regime:
            - Low volatility: 1.5x ATR (tighter stops)
            - Normal volatility: 2.25x ATR
            - High volatility: 3x ATR (wider stops to avoid noise)

        The stop distance is also constrained by minimum and maximum percentages
        of the entry price to ensure stops are neither too tight nor too wide.

        Args:
            symbol: Trading symbol (e.g., "EURUSD", "GBPUSD", "V10", "V100")
            entry_price: Entry price for the position
            direction: "BUY" or "SELL"

        Returns:
            Tuple of (stop_loss_price, stop_distance_pct, volatility_regime)
            - stop_loss_price: Calculated stop loss price
            - stop_distance_pct: Stop distance as percentage of entry price
            - volatility_regime: Detected volatility regime ("low", "normal", "high")
        """
        try:
            # Fetch price data for ATR calculation
            price_data = self._fetch_price_data(symbol)

            if price_data is None or len(price_data) < self._atr_lookback:
                logger.warning(
                    f"Insufficient price data for {symbol} to calculate dynamic stop. "
                    f"Using default stop (2% away from entry)."
                )
                # Fallback: use 2% stop distance
                stop_distance_pct = 2.0
                if direction.upper() == "BUY":
                    stop_loss = entry_price * (1 - stop_distance_pct / 100)
                else:
                    stop_loss = entry_price * (1 + stop_distance_pct / 100)
                return stop_loss, stop_distance_pct, "unknown"

            # Calculate ATR values
            atr_values = self._calculate_atr(price_data, self._atr_period)

            if len(atr_values) < self._atr_lookback:
                logger.warning(
                    f"Insufficient ATR values for {symbol}. "
                    f"Using default stop (2% away from entry)."
                )
                stop_distance_pct = 2.0
                if direction.upper() == "BUY":
                    stop_loss = entry_price * (1 - stop_distance_pct / 100)
                else:
                    stop_loss = entry_price * (1 + stop_distance_pct / 100)
                return stop_loss, stop_distance_pct, "unknown"

            # Get current ATR (most recent)
            current_atr = atr_values.iloc[-1]

            # Calculate average ATR over lookback period
            average_atr = atr_values.iloc[-self._atr_lookback:].mean()

            # Detect volatility regime
            volatility_ratio = current_atr / average_atr if average_atr > 0 else 1.0
            volatility_regime, atr_multiplier = self._detect_volatility_regime(volatility_ratio)

            # Calculate initial stop distance using ATR
            atr_stop_distance = current_atr * atr_multiplier

            # Calculate stop as percentage of price
            atr_stop_distance_pct = (atr_stop_distance / entry_price) * 100

            # Apply minimum and maximum stop distance constraints
            final_stop_distance_pct = max(
                self._min_stop_distance_pct,
                min(self._max_stop_distance_pct, atr_stop_distance_pct)
            )

            # Recalculate stop distance in price units with constrained percentage
            final_stop_distance = entry_price * (final_stop_distance_pct / 100)

            # Calculate final stop loss price
            if direction.upper() == "BUY":
                stop_loss = entry_price - final_stop_distance
            else:  # SELL
                stop_loss = entry_price + final_stop_distance

            # Generate detailed reason
            if volatility_regime == "low":
                regime_description = (
                    f"Low volatility detected (current ATR is {volatility_ratio:.2f}x average). "
                    f"Using tighter stop ({atr_multiplier}x ATR = {atr_stop_distance:.6f}) "
                    f"to maximize risk/reward ratio."
                )
            elif volatility_regime == "high":
                regime_description = (
                    f"High volatility detected (current ATR is {volatility_ratio:.2f}x average). "
                    f"Using wider stop ({atr_multiplier}x ATR = {atr_stop_distance:.6f}) "
                    f"to avoid being stopped out by market noise."
                )
            else:
                regime_description = (
                    f"Normal volatility conditions (current ATR is {volatility_ratio:.2f}x average). "
                    f"Using standard stop ({atr_multiplier}x ATR = {atr_stop_distance:.6f})."
                )

            # Note if constraints were applied
            constraint_note = ""
            if final_stop_distance_pct != atr_stop_distance_pct:
                if final_stop_distance_pct == self._min_stop_distance_pct:
                    constraint_note = (
                        f" ATR-based stop ({atr_stop_distance_pct:.3f}%) was too tight, "
                        f"applied minimum constraint ({self._min_stop_distance_pct:.1f}%)."
                    )
                elif final_stop_distance_pct == self._max_stop_distance_pct:
                    constraint_note = (
                        f" ATR-based stop ({atr_stop_distance_pct:.3f}%) was too wide, "
                        f"applied maximum constraint ({self._max_stop_distance_pct:.1f}%)."
                    )

            reason = (
                f"Dynamic stop calculation for {symbol} {direction} position. "
                f"Entry: {entry_price:.6f}, Current ATR: {current_atr:.6f}, "
                f"Average ATR: {average_atr:.6f}. {regime_description}"
                f" Stop: {stop_loss:.6f}, Distance: {final_stop_distance_pct:.3f}%."
                f"{constraint_note}"
            )

            # Create and store dynamic stop adjustment record
            adjustment = DynamicStopAdjustment(
                timestamp=datetime.utcnow(),
                symbol=symbol,
                entry_price=entry_price,
                direction=direction.upper(),
                current_atr=float(current_atr),
                atr_multiplier=atr_multiplier,
                volatility_regime=volatility_regime,
                calculated_stop=stop_loss,
                stop_distance_pct=final_stop_distance_pct,
                reason=reason,
            )

            self._dynamic_stop_adjustments.append(adjustment)
            self._store_dynamic_stop_adjustment(adjustment)

            # Log the calculation
            logger.info(
                f"Dynamic stop calculated for {symbol} {direction}: "
                f"Entry={entry_price:.6f}, Stop={stop_loss:.6f}, "
                f"Distance={final_stop_distance_pct:.3f}%, "
                f"Regime={volatility_regime}, ATR={current_atr:.6f}, "
                f"Multiplier={atr_multiplier:.2f}x"
            )

            return stop_loss, final_stop_distance_pct, volatility_regime

        except Exception as e:
            logger.error(f"Error calculating dynamic stop for {symbol}: {e}")
            # Fallback: use 2% stop distance
            stop_distance_pct = 2.0
            if direction.upper() == "BUY":
                stop_loss = entry_price * (1 - stop_distance_pct / 100)
            else:
                stop_loss = entry_price * (1 + stop_distance_pct / 100)
            return stop_loss, stop_distance_pct, "error"

    def _detect_volatility_regime(self, volatility_ratio: float) -> tuple[str, float]:
        """
        Detect volatility regime and return appropriate ATR multiplier for stop loss.

        Volatility regimes are classified based on the ratio of current ATR to
        average ATR over the lookback period:
        - Low volatility: ratio < 0.8 (use 1.5x ATR for tighter stops)
        - Normal volatility: 0.8 <= ratio <= 1.2 (use 2.25x ATR)
        - High volatility: ratio > 1.2 (use 3x ATR for wider stops)

        Args:
            volatility_ratio: Ratio of current ATR to average ATR

        Returns:
            Tuple of (volatility_regime, atr_multiplier)
            - volatility_regime: "low", "normal", or "high"
            - atr_multiplier: ATR multiplier to use for stop calculation
        """
        if volatility_ratio < 0.8:
            # Low volatility - use tighter stops
            return "low", self._low_volatility_atr_multiplier
        elif volatility_ratio > 1.2:
            # High volatility - use wider stops
            return "high", self._high_volatility_atr_multiplier
        else:
            # Normal volatility - use intermediate multiplier
            return "normal", (self._low_volatility_atr_multiplier + self._high_volatility_atr_multiplier) / 2

    def get_dynamic_stop_adjustments(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> list[DynamicStopAdjustment]:
        """
        Get dynamic stop adjustment history.

        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of adjustments to return

        Returns:
            List of DynamicStopAdjustment records
        """
        if symbol is None:
            return self._dynamic_stop_adjustments[-limit:]
        return [d for d in self._dynamic_stop_adjustments if d.symbol == symbol][-limit:]

    def _store_dynamic_stop_adjustment(self, adjustment: DynamicStopAdjustment) -> None:
        """
        Store a dynamic stop adjustment in the database.

        Args:
            adjustment: DynamicStopAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO dynamic_stop_adjustments (
                    timestamp, symbol, entry_price, direction,
                    current_atr, atr_multiplier, volatility_regime,
                    calculated_stop, stop_distance_pct, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.symbol,
                adjustment.entry_price,
                adjustment.direction,
                adjustment.current_atr,
                adjustment.atr_multiplier,
                adjustment.volatility_regime,
                adjustment.calculated_stop,
                adjustment.stop_distance_pct,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Dynamic stop adjustment stored in database for {adjustment.symbol}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store dynamic stop adjustment in database: {e}")

    def calculate_optimal_tp(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
    ) -> tuple[float, float, float]:
        """
        Calculate optimal profit target (take profit) based on ATR and win rate.

        This method implements dynamic profit target optimization that adapts to both
        market volatility (ATR) and recent trading performance. Higher win rates allow
        for tighter profit targets to maximize turnover, while lower win rates use
        wider targets to give trades more room to develop.

        Formula:
            tp = entry ± (ATR * multiplier)
            Where multiplier varies based on win rate:
            - High win rate (> 60%): 2x ATR (tighter TP for more frequent wins)
            - Low win rate (<= 60%): 3x ATR (wider TP to give trades room)

        The TP distance is constrained between 1x and 5x ATR to ensure targets
        are neither too aggressive nor too conservative.

        Args:
            symbol: Trading symbol (e.g., "EURUSD", "GBPUSD", "V10", "V100")
            entry_price: Entry price for the position
            direction: "BUY" or "SELL"

        Returns:
            Tuple of (take_profit_price, tp_distance_pct, current_win_rate)
            - take_profit_price: Calculated take profit price
            - tp_distance_pct: TP distance as percentage of entry price
            - current_win_rate: Current win rate used for calculation
        """
        try:
            # Fetch price data for ATR calculation
            price_data = self._fetch_price_data(symbol)

            if price_data is None or len(price_data) < self._atr_lookback:
                logger.warning(
                    f"Insufficient price data for {symbol} to calculate optimal TP. "
                    f"Using default TP (3x ATR estimate)."
                )
                # Fallback: use 3% TP distance as default
                tp_distance_pct = 3.0
                if direction.upper() == "BUY":
                    take_profit = entry_price * (1 + tp_distance_pct / 100)
                else:
                    take_profit = entry_price * (1 - tp_distance_pct / 100)
                return take_profit, tp_distance_pct, 50.0

            # Calculate ATR values
            atr_values = self._calculate_atr(price_data, self._atr_period)

            if len(atr_values) < self._atr_lookback:
                logger.warning(
                    f"Insufficient ATR values for {symbol}. "
                    f"Using default TP (3x ATR estimate)."
                )
                tp_distance_pct = 3.0
                if direction.upper() == "BUY":
                    take_profit = entry_price * (1 + tp_distance_pct / 100)
                else:
                    take_profit = entry_price * (1 - tp_distance_pct / 100)
                return take_profit, tp_distance_pct, 50.0

            # Get current ATR (most recent)
            current_atr = atr_values.iloc[-1]

            # Get current win rate
            recent_outcomes = self._get_recent_trade_outcomes()
            current_win_rate = self._calculate_win_rate(recent_outcomes)

            # Determine ATR multiplier based on win rate
            # Higher win rate = tighter TP (more frequent wins)
            # Lower win rate = wider TP (give trades room to develop)
            if current_win_rate > self._win_rate_threshold:
                atr_multiplier = self._high_win_rate_tp_multiplier
                multiplier_rationale = "high"
            else:
                atr_multiplier = self._low_win_rate_tp_multiplier
                multiplier_rationale = "low"

            # Apply min/max constraints to ATR multiplier
            atr_multiplier = max(
                self._min_tp_atr_multiplier,
                min(self._max_tp_atr_multiplier, atr_multiplier)
            )

            # Calculate initial TP distance using ATR
            atr_tp_distance = current_atr * atr_multiplier

            # Calculate TP as percentage of price
            atr_tp_distance_pct = (atr_tp_distance / entry_price) * 100

            # Apply minimum and maximum TP distance constraints (1x to 5x ATR)
            # Note: These are ATR-based constraints, not percentage-based
            # So we recalculate with constrained ATR multiplier
            if atr_multiplier < self._min_tp_atr_multiplier:
                atr_multiplier = self._min_tp_atr_multiplier
            elif atr_multiplier > self._max_tp_atr_multiplier:
                atr_multiplier = self._max_tp_atr_multiplier

            # Recalculate TP distance with constrained multiplier
            final_tp_distance = current_atr * atr_multiplier
            final_tp_distance_pct = (final_tp_distance / entry_price) * 100

            # Calculate final take profit price
            if direction.upper() == "BUY":
                take_profit = entry_price + final_tp_distance
            else:  # SELL
                take_profit = entry_price - final_tp_distance

            # Generate detailed reason
            if current_win_rate > self._win_rate_threshold:
                win_rate_description = (
                    f"High win rate detected ({current_win_rate:.1f}% > {self._win_rate_threshold:.1f}%). "
                    f"Using tighter TP ({atr_multiplier}x ATR) to capitalize on edge and increase turnover."
                )
            else:
                win_rate_description = (
                    f"Low/moderate win rate ({current_win_rate:.1f}% <= {self._win_rate_threshold:.1f}%). "
                    f"Using wider TP ({atr_multiplier}x ATR) to give trades room to develop."
                )

            constraint_note = ""
            if atr_multiplier == self._min_tp_atr_multiplier and atr_multiplier != self._high_win_rate_tp_multiplier:
                constraint_note = (
                    f" Applied minimum constraint (1x ATR = {final_tp_distance:.6f})."
                )
            elif atr_multiplier == self._max_tp_atr_multiplier and atr_multiplier != self._low_win_rate_tp_multiplier:
                constraint_note = (
                    f" Applied maximum constraint (5x ATR = {final_tp_distance:.6f})."
                )

            reason = (
                f"Optimal TP calculation for {symbol} {direction} position. "
                f"Entry: {entry_price:.6f}, Current ATR: {current_atr:.6f}, "
                f"Win rate: {current_win_rate:.1f}%. {win_rate_description}"
                f" TP: {take_profit:.6f}, Distance: {final_tp_distance_pct:.3f}% "
                f"({atr_multiplier}x ATR = {final_tp_distance:.6f}).{constraint_note}"
            )

            # Create and store profit target adjustment record
            adjustment = ProfitTargetAdjustment(
                timestamp=datetime.utcnow(),
                symbol=symbol,
                entry_price=entry_price,
                direction=direction.upper(),
                current_atr=float(current_atr),
                win_rate=current_win_rate,
                atr_multiplier=atr_multiplier,
                calculated_tp=take_profit,
                tp_distance_pct=final_tp_distance_pct,
                reason=reason,
            )

            self._profit_target_adjustments.append(adjustment)
            self._store_profit_target_adjustment(adjustment)

            # Log the calculation
            logger.info(
                f"Optimal TP calculated for {symbol} {direction}: "
                f"Entry={entry_price:.6f}, TP={take_profit:.6f}, "
                f"Distance={final_tp_distance_pct:.3f}%, "
                f"Win rate={current_win_rate:.1f}%, ATR={current_atr:.6f}, "
                f"Multiplier={atr_multiplier:.2f}x"
            )

            return take_profit, final_tp_distance_pct, current_win_rate

        except Exception as e:
            logger.error(f"Error calculating optimal TP for {symbol}: {e}")
            # Fallback: use 3% TP distance
            tp_distance_pct = 3.0
            if direction.upper() == "BUY":
                take_profit = entry_price * (1 + tp_distance_pct / 100)
            else:
                take_profit = entry_price * (1 - tp_distance_pct / 100)
            return take_profit, tp_distance_pct, 50.0

    def track_tp_hit(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        tp_price: float,
        atr_multiplier: float,
        exit_price: float,
        holding_time_hours: float,
    ) -> bool:
        """
        Track whether a profit target was hit and record the result.

        This method records the outcome of a trade's profit target in the database
        for analysis. It helps track the effectiveness of different TP strategies
        and optimize the multipliers over time.

        Args:
            symbol: Trading symbol
            entry_price: Entry price for the position
            direction: "BUY" or "SELL"
            tp_price: The original profit target price
            atr_multiplier: ATR multiplier used for the TP calculation
            exit_price: Actual exit price
            holding_time_hours: How long the position was held

        Returns:
            True if TP was hit, False otherwise
        """
        try:
            # Determine if TP was hit
            if direction.upper() == "BUY":
                tp_hit = exit_price >= tp_price
            else:  # SELL
                tp_hit = exit_price <= tp_price

            # Store the tracking record
            self._store_tp_hit_tracking(
                symbol=symbol,
                entry_price=entry_price,
                direction=direction,
                tp_price=tp_price,
                atr_multiplier=atr_multiplier,
                tp_hit=tp_hit,
                exit_price=exit_price,
                holding_time_hours=holding_time_hours,
            )

            # Log the result
            logger.info(
                f"TP tracking for {symbol} {direction}: "
                f"Entry={entry_price:.6f}, TP={tp_price:.6f}, Exit={exit_price:.6f}, "
                f"TP_hit={tp_hit}, ATR_mult={atr_multiplier:.2f}x, "
                f"Holding_time={holding_time_hours:.2f}h"
            )

            return tp_hit

        except Exception as e:
            logger.error(f"Error tracking TP hit for {symbol}: {e}")
            return False

    def get_tp_hit_rate(
        self,
        symbol: Optional[str] = None,
        atr_multiplier: Optional[float] = None,
        limit: int = 1000,
    ) -> tuple[float, int]:
        """
        Calculate the TP hit rate for analysis.

        This method analyzes historical TP hit data to calculate the percentage
        of trades that hit their profit target. This can be used to optimize
        TP multipliers for better performance.

        Args:
            symbol: Optional symbol to filter by
            atr_multiplier: Optional ATR multiplier to filter by
            limit: Maximum number of records to analyze

        Returns:
            Tuple of (hit_rate, total_trades)
            - hit_rate: Percentage of trades that hit TP (0-100)
            - total_trades: Total number of trades analyzed
        """
        try:
            if self._connection is None:
                logger.warning("Database connection not available for TP hit rate calculation")
                return 0.0, 0

            cursor = self._connection.cursor()

            # Build query with optional filters
            query = "SELECT tp_hit, COUNT(*) FROM tp_hit_tracking WHERE 1=1"
            params = []

            if symbol is not None:
                query += " AND symbol = ?"
                params.append(symbol)

            if atr_multiplier is not None:
                query += " AND atr_multiplier = ?"
                params.append(atr_multiplier)

            query += " GROUP BY tp_hit"

            cursor.execute(query, params)
            results = cursor.fetchall()

            if not results:
                return 0.0, 0

            # Calculate hit rate
            hit_count = 0
            total_count = 0

            for tp_hit, count in results:
                if tp_hit:
                    hit_count = count
                total_count += count

            if total_count == 0:
                return 0.0, 0

            hit_rate = (hit_count / total_count) * 100

            logger.info(
                f"TP hit rate calculated: {hit_rate:.1f}% "
                f"({hit_count}/{total_count} trades hit TP)"
            )

            return hit_rate, total_count

        except sqlite3.Error as e:
            logger.error(f"Failed to calculate TP hit rate: {e}")
            return 0.0, 0

    def get_profit_target_adjustments(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> list[ProfitTargetAdjustment]:
        """
        Get profit target adjustment history.

        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of adjustments to return

        Returns:
            List of ProfitTargetAdjustment records
        """
        if symbol is None:
            return self._profit_target_adjustments[-limit:]
        return [p for p in self._profit_target_adjustments if p.symbol == symbol][-limit:]

    def _store_profit_target_adjustment(self, adjustment: ProfitTargetAdjustment) -> None:
        """
        Store a profit target adjustment in the database.

        Args:
            adjustment: ProfitTargetAdjustment to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, adjustment not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO profit_target_adjustments (
                    timestamp, symbol, entry_price, direction,
                    current_atr, win_rate, atr_multiplier,
                    calculated_tp, tp_distance_pct, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                adjustment.timestamp.isoformat(),
                adjustment.symbol,
                adjustment.entry_price,
                adjustment.direction,
                adjustment.current_atr,
                adjustment.win_rate,
                adjustment.atr_multiplier,
                adjustment.calculated_tp,
                adjustment.tp_distance_pct,
                adjustment.reason,
            ))

            self._connection.commit()

            logger.debug(f"Profit target adjustment stored in database for {adjustment.symbol}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store profit target adjustment in database: {e}")

    def _store_tp_hit_tracking(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        tp_price: float,
        atr_multiplier: float,
        tp_hit: bool,
        exit_price: float,
        holding_time_hours: float,
    ) -> None:
        """
        Store a TP hit tracking record in the database.

        Args:
            symbol: Trading symbol
            entry_price: Entry price for the position
            direction: "BUY" or "SELL"
            tp_price: The original profit target price
            atr_multiplier: ATR multiplier used for the TP calculation
            tp_hit: Whether the TP was hit
            exit_price: Actual exit price
            holding_time_hours: How long the position was held
        """
        if self._connection is None:
            logger.warning("Database connection not available, TP tracking not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO tp_hit_tracking (
                    timestamp, symbol, entry_price, direction,
                    tp_price, atr_multiplier, tp_hit, exit_price, holding_time_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                symbol,
                entry_price,
                direction.upper(),
                tp_price,
                atr_multiplier,
                tp_hit,
                exit_price,
                holding_time_hours,
            ))

            self._connection.commit()

            logger.debug(f"TP hit tracking stored in database for {symbol}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store TP hit tracking in database: {e}")
