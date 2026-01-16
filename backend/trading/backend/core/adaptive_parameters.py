"""
Adaptive Parameters for Active Trade Management.

This module implements adaptive parameter management that adjusts trade
management parameters based on market conditions, volatility, and recent
performance to optimize trading results.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .trade_state import TradePosition
from .holding_time_optimizer import MarketRegime
from .trailing_stop_manager import TrailingStopConfig
from .partial_profit_manager import PartialProfitConfig
from .holding_time_optimizer import HoldingTimeConfig
from .scale_in_manager import ScaleInConfig


# Configure logging
logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """
    Volatility regime types for parameter adjustment.

    Regimes:
        LOW: Low volatility, stable market conditions
        NORMAL: Normal volatility, typical market conditions
        HIGH: High volatility, turbulent market conditions
        EXTREME: Extreme volatility, crisis conditions
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class PerformanceMetrics:
    """
    Recent performance metrics for parameter adjustment.

    Attributes:
        win_rate: Percentage of winning trades (0-100)
        profit_factor: Ratio of total profit to total loss
        average_win: Average profit per winning trade
        average_loss: Average loss per losing trade
        total_trades: Total number of trades in period
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown: Maximum drawdown percentage
        average_holding_time: Average time positions held
    """

    win_rate: float = 50.0
    profit_factor: float = 1.0
    average_win: float = 0.0
    average_loss: float = 0.0
    total_trades: int = 0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    average_holding_time: timedelta = field(default_factory=lambda: timedelta(0))

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage."""
        return {
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "average_win": round(self.average_win, 2),
            "average_loss": round(self.average_loss, 2),
            "total_trades": self.total_trades,
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "average_holding_time_seconds": int(self.average_holding_time.total_seconds()),
        }


@dataclass
class AdaptiveParameters:
    """
    Current adaptive parameter values.

    Attributes:
        trailing_atr_multiplier: ATR multiplier for trailing stops
        partial_profit_1r: R multiple for first partial profit (50%)
        partial_profit_2r: R multiple for second partial profit (25%)
        holding_time_trending: Max hours in trending regime
        holding_time_ranging: Max hours in ranging regime
        holding_time_volatile: Max hours in volatile regime
        scale_in_enabled: Whether scale-in is allowed
        scale_in_max_factor: Maximum scale-in factor as percentage
        breakeven_trigger_r: R multiple for breakeven trigger
        volatility_regime: Current volatility regime
        market_regime: Current market regime
        last_updated: When parameters were last updated
        update_reason: Reason for last update
    """

    trailing_atr_multiplier: float = 2.0
    partial_profit_1r: float = 2.0
    partial_profit_2r: float = 3.0
    holding_time_trending: float = 4.0
    holding_time_ranging: float = 2.0
    holding_time_volatile: float = 1.0
    scale_in_enabled: bool = True
    scale_in_max_factor: float = 200.0
    breakeven_trigger_r: float = 1.5
    volatility_regime: VolatilityRegime = VolatilityRegime.NORMAL
    market_regime: MarketRegime = MarketRegime.RANGING
    last_updated: datetime = field(default_factory=datetime.utcnow)
    update_reason: str = "Initial parameters"

    def to_dict(self) -> dict[str, Any]:
        """Convert parameters to dictionary for storage."""
        return {
            "trailing_atr_multiplier": round(self.trailing_atr_multiplier, 2),
            "partial_profit_1r": round(self.partial_profit_1r, 2),
            "partial_profit_2r": round(self.partial_profit_2r, 2),
            "holding_time_trending": round(self.holding_time_trending, 2),
            "holding_time_ranging": round(self.holding_time_ranging, 2),
            "holding_time_volatile": round(self.holding_time_volatile, 2),
            "scale_in_enabled": self.scale_in_enabled,
            "scale_in_max_factor": round(self.scale_in_max_factor, 2),
            "breakeven_trigger_r": round(self.breakeven_trigger_r, 2),
            "volatility_regime": self.volatility_regime.value,
            "market_regime": self.market_regime.value,
            "last_updated": self.last_updated.isoformat(),
            "update_reason": self.update_reason,
        }


@dataclass
class ParameterUpdate:
    """
    Record of a parameter update.

    Attributes:
        timestamp: When the update occurred
        old_parameters: Previous parameter values
        new_parameters: New parameter values
        performance_metrics: Performance metrics that triggered update
        volatility_regime: Volatility regime at time of update
        market_regime: Market regime at time of update
        reason: Explanation for the parameter change
    """

    timestamp: datetime
    old_parameters: AdaptiveParameters
    new_parameters: AdaptiveParameters
    performance_metrics: PerformanceMetrics
    volatility_regime: VolatilityRegime
    market_regime: MarketRegime
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert update to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "old_parameters": self.old_parameters.to_dict(),
            "new_parameters": self.new_parameters.to_dict(),
            "performance_metrics": self.performance_metrics.to_dict(),
            "volatility_regime": self.volatility_regime.value,
            "market_regime": self.market_regime.value,
            "reason": self.reason,
        }


@dataclass
class OptimizationResult:
    """
    Result of parameter optimization on historical data.

    Attributes:
        parameters: Tested parameter values
        sharpe_ratio: Sharpe ratio with these parameters
        win_rate: Win rate with these parameters
        profit_factor: Profit factor with these parameters
        total_profit: Total profit with these parameters
        max_drawdown: Maximum drawdown with these parameters
        total_trades: Total number of trades tested
    """

    parameters: AdaptiveParameters
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_profit: float
    max_drawdown: float
    total_trades: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for storage."""
        return {
            "parameters": self.parameters.to_dict(),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "total_profit": round(self.total_profit, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "total_trades": self.total_trades,
        }


class AdaptiveParametersManager:
    """
    Manages adaptive parameters for active trade management.

    Features:
    - Adjusts trailing distance based on volatility (2x ATR in normal, 3x ATR in high vol)
    - Adjusts partial profit levels based on recent win rate
    - Adjusts holding time limits based on regime
    - Adjusts scale-in rules based on account risk
    - Implements parameter optimization on historical data
    - Stores adaptive parameters in database
    - Logs parameter changes with reasoning
    - Updates parameters weekly based on performance

    Usage:
        manager = AdaptiveParametersManager(database_path="adaptive_params.db")

        # Get current parameters
        params = manager.get_current_parameters()

        # Update based on performance
        new_params = await manager.update_parameters(performance_metrics, market_regime)

        # Get optimized parameters for testing
        optimized = await manager.optimize_parameters(historical_data)
    """

    def __init__(
        self,
        database_path: str = "adaptive_parameters.db",
        update_interval_days: int = 7,
    ):
        """
        Initialize the AdaptiveParametersManager.

        Args:
            database_path: Path to SQLite database for storing parameters
            update_interval_days: Days between parameter updates (default: 7)
        """
        self._database_path = database_path
        self._update_interval_days = update_interval_days
        self._connection: Optional[sqlite3.Connection] = None
        self._current_parameters = AdaptiveParameters()
        self._update_history: list[ParameterUpdate] = []

        # Initialize database
        self._initialize_database()

        # Load latest parameters from database
        self._load_latest_parameters()

        logger.info(
            f"AdaptiveParametersManager initialized with database: {database_path}"
        )

    def _initialize_database(self) -> None:
        """
        Initialize the SQLite database with required tables.

        Creates tables for:
        - adaptive_parameters: Parameter snapshots
        - parameter_updates: Update history
        - optimization_results: Optimization test results
        """
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create adaptive_parameters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trailing_atr_multiplier REAL NOT NULL,
                    partial_profit_1r REAL NOT NULL,
                    partial_profit_2r REAL NOT NULL,
                    holding_time_trending REAL NOT NULL,
                    holding_time_ranging REAL NOT NULL,
                    holding_time_volatile REAL NOT NULL,
                    scale_in_enabled INTEGER NOT NULL,
                    scale_in_max_factor REAL NOT NULL,
                    breakeven_trigger_r REAL NOT NULL,
                    volatility_regime TEXT NOT NULL,
                    market_regime TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    update_reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create parameter_updates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parameter_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    old_parameters TEXT NOT NULL,
                    new_parameters TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    volatility_regime TEXT NOT NULL,
                    market_regime TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create optimization_results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parameters TEXT NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    profit_factor REAL NOT NULL,
                    total_profit REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    test_date TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_params_created
                ON adaptive_parameters(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_updates_timestamp
                ON parameter_updates(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_optimization_date
                ON optimization_results(test_date DESC)
            """)

            self._connection.commit()

            logger.info("Adaptive parameters database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_latest_parameters(self) -> None:
        """
        Load the latest parameter values from the database.

        If no parameters exist in the database, uses default values.
        """
        if self._connection is None:
            logger.warning("Database connection not available, using default parameters")
            return

        try:
            cursor = self._connection.cursor()

            # Get the most recent parameters
            cursor.execute("""
                SELECT trailing_atr_multiplier, partial_profit_1r, partial_profit_2r,
                       holding_time_trending, holding_time_ranging, holding_time_volatile,
                       scale_in_enabled, scale_in_max_factor, breakeven_trigger_r,
                       volatility_regime, market_regime, last_updated, update_reason
                FROM adaptive_parameters
                ORDER BY created_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()

            if row:
                self._current_parameters = AdaptiveParameters(
                    trailing_atr_multiplier=row[0],
                    partial_profit_1r=row[1],
                    partial_profit_2r=row[2],
                    holding_time_trending=row[3],
                    holding_time_ranging=row[4],
                    holding_time_volatile=row[5],
                    scale_in_enabled=bool(row[6]),
                    scale_in_max_factor=row[7],
                    breakeven_trigger_r=row[8],
                    volatility_regime=VolatilityRegime(row[9]),
                    market_regime=MarketRegime(row[10]),
                    last_updated=datetime.fromisoformat(row[11]),
                    update_reason=row[12],
                )
                logger.info(f"Loaded latest parameters from {row[11]}")
            else:
                logger.info("No saved parameters found, using defaults")

        except sqlite3.Error as e:
            logger.error(f"Failed to load parameters from database: {e}")

    def get_current_parameters(self) -> AdaptiveParameters:
        """
        Get the current adaptive parameter values.

        Returns:
            AdaptiveParameters with current values
        """
        return self._current_parameters

    def _calculate_volatility_regime(
        self, atr_values: list[float], atr_period: int = 14
    ) -> VolatilityRegime:
        """
        Determine current volatility regime based on ATR values.

        Args:
            atr_values: List of recent ATR values
            atr_period: Period for ATR calculation (minimum required values)

        Returns:
            VolatilityRegime classification
        """
        # Require at least 5 values for meaningful calculation
        min_values = 5
        if not atr_values or len(atr_values) < min_values:
            logger.debug(f"Insufficient ATR data (need {min_values}, have {len(atr_values)}), using NORMAL volatility regime")
            return VolatilityRegime.NORMAL

        # Calculate average ATR and current ATR
        avg_atr = sum(atr_values) / len(atr_values)
        current_atr = atr_values[-1]

        # Calculate ATR change percentage
        atr_change_pct = ((current_atr - avg_atr) / avg_atr) * 100 if avg_atr > 0 else 0

        # Classify volatility regime
        if atr_change_pct > 40:
            regime = VolatilityRegime.EXTREME
            reason = f"ATR increased by {atr_change_pct:.1f}% (extreme volatility)"
        elif atr_change_pct > 15:
            regime = VolatilityRegime.HIGH
            reason = f"ATR increased by {atr_change_pct:.1f}% (high volatility)"
        elif atr_change_pct < -15:
            regime = VolatilityRegime.LOW
            reason = f"ATR decreased by {abs(atr_change_pct):.1f}% (low volatility)"
        else:
            regime = VolatilityRegime.NORMAL
            reason = f"ATR change {atr_change_pct:.1f}% (normal volatility)"

        logger.debug(f"Volatility regime: {regime.value} - {reason}")

        return regime

    def _adjust_trailing_distance(
        self, volatility_regime: VolatilityRegime, current_params: AdaptiveParameters
    ) -> float:
        """
        Adjust trailing stop distance based on volatility.

        Args:
            volatility_regime: Current volatility regime
            current_params: Current parameter values

        Returns:
            New ATR multiplier for trailing stops
        """
        # Base multiplier
        base_multiplier = 2.0

        # Adjust based on volatility
        if volatility_regime == VolatilityRegime.LOW:
            # Tighter stops in low volatility
            new_multiplier = 1.5
            reason = "Low volatility - using tighter trailing stops (1.5x ATR)"
        elif volatility_regime == VolatilityRegime.NORMAL:
            # Normal trailing distance
            new_multiplier = 2.0
            reason = "Normal volatility - using standard trailing stops (2x ATR)"
        elif volatility_regime == VolatilityRegime.HIGH:
            # Wider stops in high volatility
            new_multiplier = 3.0
            reason = "High volatility - using wider trailing stops (3x ATR)"
        else:  # EXTREME
            # Much wider stops in extreme volatility
            new_multiplier = 4.0
            reason = "Extreme volatility - using very wide trailing stops (4x ATR)"

        logger.debug(f"Trailing ATR multiplier adjusted: {current_params.trailing_atr_multiplier:.2f} -> {new_multiplier:.2f} - {reason}")

        return new_multiplier

    def _adjust_partial_profit_levels(
        self, performance: PerformanceMetrics, current_params: AdaptiveParameters
    ) -> tuple[float, float]:
        """
        Adjust partial profit levels based on recent win rate.

        Args:
            performance: Recent performance metrics
            current_params: Current parameter values

        Returns:
            Tuple of (partial_profit_1r, partial_profit_2r) values
        """
        # Base levels
        base_1r = 2.0
        base_2r = 3.0

        # Adjust based on win rate
        if performance.win_rate >= 60:
            # High win rate - can afford to hold for larger profits
            new_1r = 2.5
            new_2r = 4.0
            reason = f"High win rate ({performance.win_rate:.1f}%) - holding for larger profits"
        elif performance.win_rate >= 50:
            # Normal win rate - standard levels
            new_1r = 2.0
            new_2r = 3.0
            reason = f"Normal win rate ({performance.win_rate:.1f}%) - using standard partial profit levels"
        elif performance.win_rate >= 40:
            # Lower win rate - bank profits earlier
            new_1r = 1.5
            new_2r = 2.5
            reason = f"Lower win rate ({performance.win_rate:.1f}%) - banking profits earlier"
        else:
            # Low win rate - bank profits very early
            new_1r = 1.0
            new_2r = 2.0
            reason = f"Low win rate ({performance.win_rate:.1f}%) - banking profits very early"

        logger.debug(f"Partial profit levels adjusted: ({current_params.partial_profit_1r:.2f}R, {current_params.partial_profit_2r:.2f}R) -> ({new_1r:.2f}R, {new_2r:.2f}R) - {reason}")

        return new_1r, new_2r

    def _adjust_holding_time_limits(
        self,
        market_regime: MarketRegime,
        volatility_regime: VolatilityRegime,
        current_params: AdaptiveParameters,
    ) -> tuple[float, float, float]:
        """
        Adjust holding time limits based on market regime and volatility.

        Args:
            market_regime: Current market regime
            volatility_regime: Current volatility regime
            current_params: Current parameter values

        Returns:
            Tuple of (trending_hours, ranging_hours, volatile_hours)
        """
        # Base holding times
        base_trending = 4.0
        base_ranging = 2.0
        base_volatile = 1.0

        # Adjust based on volatility
        volatility_multiplier = 1.0
        if volatility_regime == VolatilityRegime.LOW:
            # Can hold longer in low volatility
            volatility_multiplier = 1.5
        elif volatility_regime == VolatilityRegime.HIGH:
            # Hold for shorter time in high volatility
            volatility_multiplier = 0.75
        elif volatility_regime == VolatilityRegime.EXTREME:
            # Hold for much shorter time in extreme volatility
            volatility_multiplier = 0.5

        new_trending = base_trending * volatility_multiplier
        new_ranging = base_ranging * volatility_multiplier
        new_volatile = base_volatile * volatility_multiplier

        reason = f"Holding times adjusted by {volatility_multiplier:.2f}x based on {volatility_regime.value} volatility"

        logger.debug(f"Holding time limits adjusted: ({current_params.holding_time_trending:.2f}h, {current_params.holding_time_ranging:.2f}h, {current_params.holding_time_volatile:.2f}h) -> ({new_trending:.2f}h, {new_ranging:.2f}h, {new_volatile:.2f}h) - {reason}")

        return new_trending, new_ranging, new_volatile

    def _adjust_scale_in_rules(
        self, performance: PerformanceMetrics, current_params: AdaptiveParameters
    ) -> tuple[bool, float]:
        """
        Adjust scale-in rules based on account risk and performance.

        Args:
            performance: Recent performance metrics
            current_params: Current parameter values

        Returns:
            Tuple of (scale_in_enabled, max_scale_factor)
        """
        # Determine if scale-in should be enabled based on drawdown
        max_allowed_drawdown = 20.0  # 20% max drawdown

        if performance.max_drawdown > max_allowed_drawdown:
            # Disable scale-in if drawdown is too high
            enabled = False
            max_factor = 100.0
            reason = f"Scale-in disabled due to high drawdown ({performance.max_drawdown:.1f}%)"
        elif performance.profit_factor < 1.0:
            # Disable scale-in if not profitable
            enabled = False
            max_factor = 100.0
            reason = f"Scale-in disabled due to low profit factor ({performance.profit_factor:.2f})"
        else:
            # Enable scale-in with adjusted max factor
            enabled = True

            # Adjust max scale factor based on performance
            if performance.sharpe_ratio > 2.0:
                # Excellent performance - allow more scaling
                max_factor = 250.0
                reason = f"Scale-in enabled at 250% (excellent Sharpe: {performance.sharpe_ratio:.2f})"
            elif performance.sharpe_ratio > 1.0:
                # Good performance - standard scaling
                max_factor = 200.0
                reason = f"Scale-in enabled at 200% (good Sharpe: {performance.sharpe_ratio:.2f})"
            else:
                # Moderate performance - conservative scaling
                max_factor = 150.0
                reason = f"Scale-in enabled at 150% (moderate Sharpe: {performance.sharpe_ratio:.2f})"

        logger.debug(f"Scale-in rules adjusted: enabled={enabled}, max_factor={max_factor:.0f}% - {reason}")

        return enabled, max_factor

    async def update_parameters(
        self,
        performance: PerformanceMetrics,
        market_regime: MarketRegime,
        atr_values: Optional[list[float]] = None,
    ) -> AdaptiveParameters:
        """
        Update adaptive parameters based on performance and market conditions.

        Args:
            performance: Recent performance metrics
            market_regime: Current market regime
            atr_values: Optional list of recent ATR values for volatility calculation

        Returns:
            Updated AdaptiveParameters
        """
        # Store old parameters
        old_parameters = AdaptiveParameters(
            trailing_atr_multiplier=self._current_parameters.trailing_atr_multiplier,
            partial_profit_1r=self._current_parameters.partial_profit_1r,
            partial_profit_2r=self._current_parameters.partial_profit_2r,
            holding_time_trending=self._current_parameters.holding_time_trending,
            holding_time_ranging=self._current_parameters.holding_time_ranging,
            holding_time_volatile=self._current_parameters.holding_time_volatile,
            scale_in_enabled=self._current_parameters.scale_in_enabled,
            scale_in_max_factor=self._current_parameters.scale_in_max_factor,
            breakeven_trigger_r=self._current_parameters.breakeven_trigger_r,
            volatility_regime=self._current_parameters.volatility_regime,
            market_regime=self._current_parameters.market_regime,
            last_updated=self._current_parameters.last_updated,
            update_reason=self._current_parameters.update_reason,
        )

        # Calculate volatility regime
        volatility_regime = self._calculate_volatility_regime(atr_values or [])

        # Adjust each parameter category
        trailing_atr = self._adjust_trailing_distance(
            volatility_regime, self._current_parameters
        )

        partial_1r, partial_2r = self._adjust_partial_profit_levels(
            performance, self._current_parameters
        )

        hold_trending, hold_ranging, hold_volatile = self._adjust_holding_time_limits(
            market_regime, volatility_regime, self._current_parameters
        )

        scale_enabled, scale_max = self._adjust_scale_in_rules(
            performance, self._current_parameters
        )

        # Create new parameters
        new_parameters = AdaptiveParameters(
            trailing_atr_multiplier=trailing_atr,
            partial_profit_1r=partial_1r,
            partial_profit_2r=partial_2r,
            holding_time_trending=hold_trending,
            holding_time_ranging=hold_ranging,
            holding_time_volatile=hold_volatile,
            scale_in_enabled=scale_enabled,
            scale_in_max_factor=scale_max,
            breakeven_trigger_r=1.5,  # Keep breakeven constant for now
            volatility_regime=volatility_regime,
            market_regime=market_regime,
            last_updated=datetime.utcnow(),
            update_reason=self._generate_update_reason(
                performance, market_regime, volatility_regime
            ),
        )

        # Create update record
        update = ParameterUpdate(
            timestamp=datetime.utcnow(),
            old_parameters=old_parameters,
            new_parameters=new_parameters,
            performance_metrics=performance,
            volatility_regime=volatility_regime,
            market_regime=market_regime,
            reason=new_parameters.update_reason,
        )

        # Store update in history
        self._update_history.append(update)

        # Update current parameters
        self._current_parameters = new_parameters

        # Store in database
        self._store_parameters(new_parameters)
        self._store_parameter_update(update)

        # Log the update
        logger.info(
            f"Parameters updated: "
            f"Trailing ATR: {old_parameters.trailing_atr_multiplier:.2f} -> {trailing_atr:.2f}, "
            f"Partial 1R: {old_parameters.partial_profit_1r:.2f} -> {partial_1r:.2f}, "
            f"Scale-in: {old_parameters.scale_in_enabled} -> {scale_enabled}, "
            f"Reason: {new_parameters.update_reason}"
        )

        return new_parameters

    def _generate_update_reason(
        self,
        performance: PerformanceMetrics,
        market_regime: MarketRegime,
        volatility_regime: VolatilityRegime,
    ) -> str:
        """
        Generate a human-readable reason for parameter update.

        Args:
            performance: Performance metrics
            market_regime: Current market regime
            volatility_regime: Current volatility regime

        Returns:
            Reason string
        """
        parts = [
            f"Win rate: {performance.win_rate:.1f}%",
            f"Profit factor: {performance.profit_factor:.2f}",
            f"Sharpe ratio: {performance.sharpe_ratio:.2f}",
            f"Market regime: {market_regime.value}",
            f"Volatility: {volatility_regime.value}",
        ]

        return " | ".join(parts)

    def _store_parameters(self, parameters: AdaptiveParameters) -> None:
        """
        Store parameter values in database.

        Args:
            parameters: AdaptiveParameters to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, parameters not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO adaptive_parameters (
                    trailing_atr_multiplier, partial_profit_1r, partial_profit_2r,
                    holding_time_trending, holding_time_ranging, holding_time_volatile,
                    scale_in_enabled, scale_in_max_factor, breakeven_trigger_r,
                    volatility_regime, market_regime, last_updated, update_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                parameters.trailing_atr_multiplier,
                parameters.partial_profit_1r,
                parameters.partial_profit_2r,
                parameters.holding_time_trending,
                parameters.holding_time_ranging,
                parameters.holding_time_volatile,
                int(parameters.scale_in_enabled),
                parameters.scale_in_max_factor,
                parameters.breakeven_trigger_r,
                parameters.volatility_regime.value,
                parameters.market_regime.value,
                parameters.last_updated.isoformat(),
                parameters.update_reason,
            ))

            self._connection.commit()

            logger.debug(f"Parameters stored in database at {parameters.last_updated}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store parameters in database: {e}")

    def _store_parameter_update(self, update: ParameterUpdate) -> None:
        """
        Store a parameter update record in database.

        Args:
            update: ParameterUpdate to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, update not stored")
            return

        try:
            cursor = self._connection.cursor()

            # Serialize complex objects to JSON strings
            import json

            cursor.execute("""
                INSERT INTO parameter_updates (
                    timestamp, old_parameters, new_parameters,
                    performance_metrics, volatility_regime, market_regime, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                update.timestamp.isoformat(),
                json.dumps(update.old_parameters.to_dict()),
                json.dumps(update.new_parameters.to_dict()),
                json.dumps(update.performance_metrics.to_dict()),
                update.volatility_regime.value,
                update.market_regime.value,
                update.reason,
            ))

            self._connection.commit()

            logger.debug(f"Parameter update stored in database at {update.timestamp}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store parameter update in database: {e}")

    def get_trailing_stop_config(self) -> TrailingStopConfig:
        """
        Get trailing stop configuration with current adaptive parameters.

        Returns:
            TrailingStopConfig with adaptive ATR multiplier
        """
        return TrailingStopConfig(
            atr_multiplier=self._current_parameters.trailing_atr_multiplier,
            atr_period=14,
            min_profit_r=1.0,
            trail_step_atr_multiplier=0.5,
            enabled=True,
        )

    def get_partial_profit_config(self) -> PartialProfitConfig:
        """
        Get partial profit configuration with current adaptive parameters.

        Returns:
            PartialProfitConfig with adaptive R levels
        """
        return PartialProfitConfig(
            close_50_at_r=self._current_parameters.partial_profit_1r,
            close_25_at_r=self._current_parameters.partial_profit_2r,
            close_remaining_at_r=5.0,
            cooldown_seconds=60,
            move_to_breakeven_after_first=True,
            enabled=True,
        )

    def get_holding_time_config(self, regime: MarketRegime) -> HoldingTimeConfig:
        """
        Get holding time configuration with current adaptive parameters.

        Args:
            regime: Market regime to get config for

        Returns:
            HoldingTimeConfig with adaptive time limits
        """
        return HoldingTimeConfig(
            trending_max_hours=self._current_parameters.holding_time_trending,
            ranging_max_hours=self._current_parameters.holding_time_ranging,
            volatile_max_hours=self._current_parameters.holding_time_volatile,
            default_regime=regime,
            close_percentage_at_limit=0.5,
            enabled=True,
        )

    def get_scale_in_config(self) -> ScaleInConfig:
        """
        Get scale-in configuration with current adaptive parameters.

        Returns:
            ScaleInConfig with adaptive scale factor
        """
        return ScaleInConfig(
            first_trigger_r=1.0,
            first_scale_percent=50.0,
            second_trigger_r=2.0,
            second_scale_percent=25.0,
            max_scale_factor=self._current_parameters.scale_in_max_factor,
            min_trend_strength=0.6,
            min_signal_quality=0.7,
            enabled=self._current_parameters.scale_in_enabled,
        )

    async def optimize_parameters(
        self, historical_data: list[dict[str, Any]]
    ) -> OptimizationResult:
        """
        Optimize parameters on historical data.

        Tests different parameter combinations and returns the best performing set.

        Args:
            historical_data: List of historical trade dictionaries containing:
                - entry_price: float
                - exit_price: float
                - profit: float
                - holding_time_seconds: int
                - peak_profit: float
                - max_drawdown: float

        Returns:
            OptimizationResult with best parameters found
        """
        logger.info(f"Starting parameter optimization on {len(historical_data)} historical trades")

        # Define parameter ranges to test
        atr_multipliers = [1.5, 2.0, 2.5, 3.0]
        partial_1r_levels = [1.5, 2.0, 2.5]
        partial_2r_levels = [2.5, 3.0, 3.5]

        best_result = None
        best_sharpe = -float("inf")

        # Test each combination
        for atr_mult in atr_multipliers:
            for p1r in partial_1r_levels:
                for p2r in partial_2r_levels:
                    # Skip invalid combinations
                    if p2r <= p1r:
                        continue

                    # Create test parameters
                    test_params = AdaptiveParameters(
                        trailing_atr_multiplier=atr_mult,
                        partial_profit_1r=p1r,
                        partial_profit_2r=p2r,
                        holding_time_trending=4.0,
                        holding_time_ranging=2.0,
                        holding_time_volatile=1.0,
                        scale_in_enabled=True,
                        scale_in_max_factor=200.0,
                        breakeven_trigger_r=1.5,
                        volatility_regime=VolatilityRegime.NORMAL,
                        market_regime=MarketRegime.RANGING,
                    )

                    # Simulate performance with these parameters
                    result = self._simulate_parameters(test_params, historical_data)

                    # Track best result
                    if result.sharpe_ratio > best_sharpe:
                        best_sharpe = result.sharpe_ratio
                        best_result = result

                    # Store result in database
                    self._store_optimization_result(result)

        if best_result:
            logger.info(
                f"Optimization complete: Best Sharpe ratio: {best_result.sharpe_ratio:.2f}, "
                f"ATR mult: {best_result.parameters.trailing_atr_multiplier:.2f}, "
                f"Partial 1R: {best_result.parameters.partial_profit_1r:.2f}"
            )
        else:
            logger.warning("Parameter optimization failed to find valid results")

        return best_result or OptimizationResult(
            parameters=self._current_parameters,
            sharpe_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_profit=0.0,
            max_drawdown=0.0,
            total_trades=0,
        )

    def _simulate_parameters(
        self, parameters: AdaptiveParameters, historical_data: list[dict[str, Any]]
    ) -> OptimizationResult:
        """
        Simulate performance with given parameters on historical data.

        Args:
            parameters: AdaptiveParameters to test
            historical_data: Historical trade data

        Returns:
            OptimizationResult with performance metrics
        """
        # Simplified simulation - in production would use full backtest engine
        profits = []
        losses = []
        total_profit = 0.0
        max_drawdown = 0.0

        for trade in historical_data:
            profit = trade.get("profit", 0.0)

            if profit > 0:
                profits.append(profit)
                total_profit += profit
            else:
                losses.append(abs(profit))
                total_profit += profit

            # Track max drawdown
            drawdown = trade.get("max_drawdown", 0.0)
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Calculate metrics
        total_trades = len(historical_data)
        winning_trades = len(profits)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        total_profit_val = sum(profits)
        total_loss_val = sum(losses)
        profit_factor = (total_profit_val / total_loss_val) if total_loss_val > 0 else 0.0

        # Simplified Sharpe ratio calculation
        # In production, would use proper risk-free rate and returns
        avg_return = total_profit / total_trades if total_trades > 0 else 0.0
        returns = [t.get("profit", 0.0) for t in historical_data]
        std_return = (
            sum((r - avg_return) ** 2 for r in returns) / len(returns)
        ) ** 0.5 if returns else 0.0
        sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0.0

        return OptimizationResult(
            parameters=parameters,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_profit=total_profit,
            max_drawdown=max_drawdown,
            total_trades=len(historical_data),
        )

    def _store_optimization_result(self, result: OptimizationResult) -> None:
        """
        Store optimization result in database.

        Args:
            result: OptimizationResult to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, result not stored")
            return

        try:
            cursor = self._connection.cursor()

            import json

            cursor.execute("""
                INSERT INTO optimization_results (
                    parameters, sharpe_ratio, win_rate, profit_factor,
                    total_profit, max_drawdown, test_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                json.dumps(result.parameters.to_dict()),
                result.sharpe_ratio,
                result.win_rate,
                result.profit_factor,
                result.total_profit,
                result.max_drawdown,
                datetime.utcnow().date().isoformat(),
            ))

            self._connection.commit()

            logger.debug(f"Optimization result stored: Sharpe={result.sharpe_ratio:.2f}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store optimization result: {e}")

    def get_update_history(self, limit: int = 100) -> list[ParameterUpdate]:
        """
        Get parameter update history.

        Args:
            limit: Maximum number of updates to return

        Returns:
            List of ParameterUpdate records
        """
        return self._update_history[-limit:]

    def should_update_parameters(self) -> bool:
        """
        Check if parameters should be updated based on time interval.

        Returns:
            True if enough time has passed since last update
        """
        time_since_update = datetime.utcnow() - self._current_parameters.last_updated
        return time_since_update.days >= self._update_interval_days

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        self.close()
