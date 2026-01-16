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


class AdaptiveRiskManager:
    """
    Manages adaptive risk based on recent trading performance.

    Features:
    - Calculates base risk percentage (default 2%)
    - Adjusts risk based on recent performance (last 20 trades)
    - Reduces risk by 50% when win rate < 50%
    - Increases risk by 25% when win rate > 70%
    - Caps minimum risk at 0.5%
    - Caps maximum risk at 3%
    - Logs all risk adjustments with reasoning
    - Stores risk adjustment history in database

    Usage:
        risk_manager = AdaptiveRiskManager(
            performance_comparator=comparator,
            database_path="adaptive_risk.db"
        )

        # Get current risk percentage
        risk_pct = risk_manager.calculate_base_risk()

        # Adjust risk based on recent performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Calculate position size for a trade
        position_size = risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=1.0850,
            stop_loss=1.0800
        )
    """

    def __init__(
        self,
        performance_comparator: PerformanceComparator,
        database_path: str = "adaptive_risk.db",
        base_risk_percent: float = 2.0,
        min_risk_percent: float = 0.5,
        max_risk_percent: float = 3.0,
        performance_window: int = 20,
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
        """
        self._performance_comparator = performance_comparator
        self._database_path = database_path
        self._base_risk_percent = base_risk_percent
        self._min_risk_percent = min_risk_percent
        self._max_risk_percent = max_risk_percent
        self._performance_window = performance_window
        self._connection: Optional[sqlite3.Connection] = None
        self._adjustment_history: list[RiskAdjustment] = []
        self._current_risk_percent = base_risk_percent

        # Initialize database
        self._initialize_database()

        # Load latest risk settings from database
        self._load_latest_risk_settings()

        logger.info(
            f"AdaptiveRiskManager initialized: base_risk={base_risk_percent}%, "
            f"min_risk={min_risk_percent}%, max_risk={max_risk_percent}%, "
            f"window={performance_window} trades"
        )

    def _initialize_database(self) -> None:
        """
        Initialize the SQLite database with required tables.

        Creates tables for:
        - risk_adjustments: Risk adjustment history
        - risk_settings: Current risk settings snapshots
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

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adjustments_timestamp
                ON risk_adjustments(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_updated
                ON risk_settings(last_updated DESC)
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
    ) -> float:
        """
        Calculate position size based on current risk percentage.

        Args:
            account_balance: Current account balance
            entry_price: Entry price for the trade
            stop_loss: Stop loss price for the trade
            direction: "BUY" or "SELL" (default: "BUY")

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

        # Calculate position size in lots
        position_size_lots = risk_amount / (risk_per_lot_price * lot_multiplier)

        logger.debug(
            f"Position size calculation: balance={account_balance:.2f}, "
            f"risk_pct={self._current_risk_percent:.2f}%, "
            f"risk_amount={risk_amount:.2f}, "
            f"risk_per_lot={risk_per_lot_price:.5f}, "
            f"position_size={position_size_lots:.2f} lots"
        )

        return position_size_lots

    def get_current_risk_percent(self) -> float:
        """
        Get the current risk percentage.

        Returns:
            Current risk percentage
        """
        return self._current_risk_percent

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
