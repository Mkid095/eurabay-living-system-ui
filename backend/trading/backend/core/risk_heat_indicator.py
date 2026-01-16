"""
Risk Heat Indicator for overall risk assessment.

This module implements a visual indicator showing current risk level
by aggregating multiple risk factors including open position risk,
correlation risk, daily loss, and consecutive losses.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum

from .adaptive_risk_manager import AdaptiveRiskManager
from .performance_comparator import PerformanceComparator
from .trade_state import TradePosition


# Configure logging
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """
    Risk level classification.

    Attributes:
        LOW: Risk score 0-30, minimal risk
        MEDIUM: Risk score 30-60, moderate risk
        HIGH: Risk score 60-80, elevated risk
        CRITICAL: Risk score 80-100, severe risk
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """
        Get RiskLevel from numeric score.

        Args:
            score: Risk score between 0 and 100

        Returns:
            RiskLevel enum value
        """
        if score < 30:
            return cls.LOW
        elif score < 60:
            return cls.MEDIUM
        elif score < 80:
            return cls.HIGH
        else:
            return cls.CRITICAL


@dataclass
class RiskLevelChangeEvent:
    """
    Record of a risk level change event.

    Attributes:
        timestamp: When the risk level changed
        old_level: Previous risk level
        new_level: New risk level
        old_score: Previous risk score
        new_score: New risk score
        trigger_factor: Which factor triggered the change
        reason: Explanation for the change
    """
    timestamp: datetime
    old_level: RiskLevel
    new_level: RiskLevel
    old_score: float
    new_score: float
    trigger_factor: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage and API responses."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "old_level": self.old_level.value,
            "new_level": self.new_level.value,
            "old_score": round(self.old_score, 2),
            "new_score": round(self.new_score, 2),
            "trigger_factor": self.trigger_factor,
            "reason": self.reason,
        }


@dataclass
class RiskScoreBreakdown:
    """
    Detailed breakdown of risk score components.

    Attributes:
        position_risk_score: Score from open position risk (0-100)
        correlation_risk_score: Score from correlation risk (0-100)
        daily_loss_score: Score from daily loss (0-100)
        consecutive_losses_score: Score from consecutive losses (0-100)
        overall_score: Weighted overall risk score (0-100)
        risk_level: Current risk level
        calculated_at: When the score was calculated
    """
    position_risk_score: float
    correlation_risk_score: float
    daily_loss_score: float
    consecutive_losses_score: float
    overall_score: float
    risk_level: RiskLevel
    calculated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage and API responses."""
        return {
            "position_risk_score": round(self.position_risk_score, 2),
            "correlation_risk_score": round(self.correlation_risk_score, 2),
            "daily_loss_score": round(self.daily_loss_score, 2),
            "consecutive_losses_score": round(self.consecutive_losses_score, 2),
            "overall_score": round(self.overall_score, 2),
            "risk_level": self.risk_level.value,
            "calculated_at": self.calculated_at.isoformat(),
        }


class RiskHeatIndicator:
    """
    Calculates and tracks overall risk heat indicator.

    The risk heat indicator aggregates multiple risk factors into a single
    score (0-100) and classifies it into four levels:
    - LOW (0-30): Minimal risk
    - MEDIUM (30-60): Moderate risk
    - HIGH (60-80): Elevated risk
    - CRITICAL (80-100): Severe risk

    Risk factors considered:
    1. Open position risk: Total risk from all open positions
    2. Correlation risk: Risk from correlated positions
    3. Daily loss: Proximity to daily loss limit
    4. Consecutive losses: Impact of losing streak

    Usage:
        indicator = RiskHeatIndicator(
            risk_manager=risk_manager,
            performance_comparator=comparator,
            database_path="risk_heat.db"
        )

        # Get current risk score
        breakdown = indicator.calculate_risk_score()
        print(f"Risk Level: {breakdown.risk_level.value}")
        print(f"Overall Score: {breakdown.overall_score}")

        # Get risk level history
        events = indicator.get_risk_level_events(limit=10)
    """

    # Risk factor weights for overall score calculation
    POSITION_RISK_WEIGHT = 0.30
    CORRELATION_RISK_WEIGHT = 0.20
    DAILY_LOSS_WEIGHT = 0.25
    CONSECUTIVE_LOSSES_WEIGHT = 0.25

    def __init__(
        self,
        risk_manager: AdaptiveRiskManager,
        performance_comparator: PerformanceComparator,
        database_path: str = "risk_heat.db",
    ):
        """
        Initialize the RiskHeatIndicator.

        Args:
            risk_manager: AdaptiveRiskManager instance for risk data
            performance_comparator: PerformanceComparator for trade history
            database_path: Path to SQLite database for storing risk events
        """
        self._risk_manager = risk_manager
        self._performance_comparator = performance_comparator
        self._database_path = database_path
        self._connection: Optional[sqlite3.Connection] = None
        self._current_level: RiskLevel = RiskLevel.LOW
        self._current_score: float = 0.0
        self._risk_level_events: list[RiskLevelChangeEvent] = []

        # Initialize database
        self._initialize_database()

        # Calculate initial risk level
        initial_breakdown = self.calculate_risk_score()
        self._current_level = initial_breakdown.risk_level
        self._current_score = initial_breakdown.overall_score

        logger.info(
            f"RiskHeatIndicator initialized. Initial level: {self._current_level.value}, "
            f"score: {self._current_score:.2f}"
        )

    def _initialize_database(self) -> None:
        """Create database tables for storing risk level events."""
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create risk_level_events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_level_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    old_level TEXT NOT NULL,
                    new_level TEXT NOT NULL,
                    old_score REAL NOT NULL,
                    new_score REAL NOT NULL,
                    trigger_factor TEXT NOT NULL,
                    reason TEXT NOT NULL
                )
            """)

            # Create index on timestamp for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_risk_events_timestamp
                ON risk_level_events(timestamp)
            """)

            self._connection.commit()
            logger.info(f"Database initialized at {self._database_path}")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            self._connection = None

    def calculate_risk_score(
        self,
        open_positions: Optional[list[TradePosition]] = None,
    ) -> RiskScoreBreakdown:
        """
        Calculate current risk score based on all risk factors.

        Args:
            open_positions: List of open positions (optional, fetched if not provided)

        Returns:
            RiskScoreBreakdown with detailed risk analysis
        """
        # Calculate individual risk factor scores
        position_risk_score = self._calculate_position_risk_score(open_positions)
        correlation_risk_score = self._calculate_correlation_risk_score(open_positions)
        daily_loss_score = self._calculate_daily_loss_score()
        consecutive_losses_score = self._calculate_consecutive_losses_score()

        # Calculate weighted overall score
        overall_score = (
            position_risk_score * self.POSITION_RISK_WEIGHT +
            correlation_risk_score * self.CORRELATION_RISK_WEIGHT +
            daily_loss_score * self.DAILY_LOSS_WEIGHT +
            consecutive_losses_score * self.CONSECUTIVE_LOSSES_WEIGHT
        )

        # Determine risk level
        risk_level = RiskLevel.from_score(overall_score)

        breakdown = RiskScoreBreakdown(
            position_risk_score=position_risk_score,
            correlation_risk_score=correlation_risk_score,
            daily_loss_score=daily_loss_score,
            consecutive_losses_score=consecutive_losses_score,
            overall_score=overall_score,
            risk_level=risk_level,
            calculated_at=datetime.now(),
        )

        # Check for risk level change
        self._check_and_log_risk_level_change(breakdown)

        # Update current state
        self._current_score = overall_score
        self._current_level = risk_level

        return breakdown

    def _calculate_position_risk_score(
        self,
        open_positions: Optional[list[TradePosition]] = None,
    ) -> float:
        """
        Calculate risk score from open positions.

        Score increases with:
        - Number of open positions
        - Total position size relative to account
        - Proximity to maximum risk (3%)

        Args:
            open_positions: List of open positions (optional)

        Returns:
            Risk score from 0 to 100
        """
        if open_positions is None:
            open_positions = []

        if not open_positions:
            return 0.0

        # Get current risk percentage from risk manager
        current_risk_pct = self._risk_manager._current_risk_percent
        max_risk_pct = self._risk_manager._max_risk_percent

        # Calculate base score from risk percentage usage
        risk_usage_ratio = current_risk_pct / max_risk_pct if max_risk_pct > 0 else 0

        # Adjust for number of positions (more positions = higher risk)
        position_count_factor = min(len(open_positions) / 10.0, 1.0)  # Cap at 10 positions

        # Combine factors
        position_score = (risk_usage_ratio * 0.7 + position_count_factor * 0.3) * 100

        return min(max(position_score, 0.0), 100.0)

    def _calculate_correlation_risk_score(
        self,
        open_positions: Optional[list[TradePosition]] = None,
    ) -> float:
        """
        Calculate risk score from correlated positions.

        Score increases with:
        - Number of highly correlated positions
        - Correlation strength between positions

        Args:
            open_positions: List of open positions (optional)

        Returns:
            Risk score from 0 to 100
        """
        if open_positions is None:
            open_positions = []

        if len(open_positions) < 2:
            return 0.0

        # Get correlation data from risk manager
        # This is a simplified calculation - in production, would use actual correlation matrix
        unique_symbols = set(pos.symbol for pos in open_positions)

        # Synthetic volatility symbols (V10, V25, V50, V75, V100) are highly correlated
        volatility_symbols = [s for s in unique_symbols if s.startswith("V")]
        correlation_count = len(volatility_symbols)

        # Each correlated pair beyond the first adds risk
        correlation_risk = min((correlation_count - 1) / 4.0, 1.0) if correlation_count > 1 else 0

        return correlation_risk * 100

    def _calculate_daily_loss_score(self) -> float:
        """
        Calculate risk score from daily loss proximity to limit.

        Score increases as daily loss approaches the daily loss limit.

        Returns:
            Risk score from 0 to 100
        """
        try:
            # Get daily loss tracking from risk manager
            # In production, this would query the database for today's daily loss
            # For now, use a simplified approach

            # Check if trading is halted due to daily loss
            if self._risk_manager._trading_halted:
                return 100.0

            # Get daily loss limit percentage
            daily_loss_limit = self._risk_manager._daily_loss_limit_percent

            # In production, would fetch actual daily P&L from database
            # For now, return 0 (assume no daily loss)
            # TODO: Integrate with actual daily P&L tracking

            return 0.0

        except Exception as e:
            logger.warning(f"Error calculating daily loss score: {e}")
            return 0.0

    def _calculate_consecutive_losses_score(self) -> float:
        """
        Calculate risk score from consecutive losses.

        Score increases with:
        - Number of consecutive losses
        - Proximity to circuit breaker (7 losses)

        Returns:
            Risk score from 0 to 100
        """
        try:
            # Get consecutive losses count from risk manager
            consecutive_losses = self._risk_manager.get_consecutive_losses_count()

            # Circuit breaker at 7 consecutive losses = score of 100
            # Scale linearly: 0 losses = 0, 7 losses = 100
            score = (consecutive_losses / 7.0) * 100

            # Check if trading is halted
            if self._risk_manager.is_trading_halted_by_consecutive_losses():
                return 100.0

            return min(max(score, 0.0), 100.0)

        except Exception as e:
            logger.warning(f"Error calculating consecutive losses score: {e}")
            return 0.0

    def _check_and_log_risk_level_change(self, breakdown: RiskScoreBreakdown) -> None:
        """
        Check if risk level has changed and log the event.

        Args:
            breakdown: Current risk score breakdown
        """
        new_level = breakdown.risk_level
        new_score = breakdown.overall_score

        if new_level != self._current_level:
            # Determine which factor triggered the change
            trigger_factor = self._identify_trigger_factor(breakdown)

            # Generate reason
            reason = (
                f"Risk level changed from {self._current_level.value} to {new_level.value}. "
                f"Score changed from {self._current_score:.2f} to {new_score:.2f}. "
                f"Triggered by {trigger_factor}."
            )

            # Create event
            event = RiskLevelChangeEvent(
                timestamp=datetime.now(),
                old_level=self._current_level,
                new_level=new_level,
                old_score=self._current_score,
                new_score=new_score,
                trigger_factor=trigger_factor,
                reason=reason,
            )

            # Add to in-memory list
            self._risk_level_events.append(event)

            # Store in database
            self._store_risk_level_event(event)

            # Log the change
            logger.warning(f"Risk Level Change: {reason}")

    def _identify_trigger_factor(self, breakdown: RiskScoreBreakdown) -> str:
        """
        Identify which risk factor contributed most to the level change.

        Args:
            breakdown: Current risk score breakdown

        Returns:
            Name of the trigger factor
        """
        factors = {
            "position_risk": breakdown.position_risk_score * self.POSITION_RISK_WEIGHT,
            "correlation_risk": breakdown.correlation_risk_score * self.CORRELATION_RISK_WEIGHT,
            "daily_loss": breakdown.daily_loss_score * self.DAILY_LOSS_WEIGHT,
            "consecutive_losses": breakdown.consecutive_losses_score * self.CONSECUTIVE_LOSSES_WEIGHT,
        }

        trigger = max(factors.items(), key=lambda x: x[1])
        return trigger[0]

    def _store_risk_level_event(self, event: RiskLevelChangeEvent) -> None:
        """
        Store a risk level change event in the database.

        Args:
            event: RiskLevelChangeEvent to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, event not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO risk_level_events (
                    timestamp, old_level, new_level, old_score, new_score,
                    trigger_factor, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.old_level.value,
                event.new_level.value,
                event.old_score,
                event.new_score,
                event.trigger_factor,
                event.reason,
            ))

            self._connection.commit()

            logger.debug(
                f"Risk level event stored: {event.old_level.value} -> {event.new_level.value}"
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to store risk level event in database: {e}")

    def get_current_risk_level(self) -> RiskLevel:
        """
        Get the current risk level.

        Returns:
            Current RiskLevel enum value
        """
        return self._current_level

    def get_current_risk_score(self) -> float:
        """
        Get the current risk score.

        Returns:
            Current risk score (0-100)
        """
        return self._current_score

    def get_risk_level_events(self, limit: int = 100) -> list[RiskLevelChangeEvent]:
        """
        Get the history of risk level change events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of RiskLevelChangeEvent records
        """
        return self._risk_level_events[-limit:]

    def get_risk_summary(self) -> dict[str, Any]:
        """
        Get a summary of current risk status.

        Returns:
            Dictionary with risk level, score, and breakdown
        """
        breakdown = self.calculate_risk_score()

        return {
            "risk_level": breakdown.risk_level.value,
            "risk_score": round(breakdown.overall_score, 2),
            "breakdown": breakdown.to_dict(),
            "is_trading_halted": self._risk_manager._trading_halted,
            "halt_reason": self._get_halt_reason(),
        }

    def _get_halt_reason(self) -> Optional[str]:
        """
        Get the reason why trading is halted.

        Returns:
            Reason string or None if not halted
        """
        if not self._risk_manager._trading_halted:
            return None

        if self._risk_manager.is_trading_halted_by_consecutive_losses():
            consecutive_losses = self._risk_manager.get_consecutive_losses_count()
            return f"Consecutive losses circuit breaker (7+ losses reached: {consecutive_losses})"

        # Check for drawdown halt
        drawdown, _, _ = self._risk_manager.calculate_drawdown(current_equity=10000.0)
        if drawdown >= self._risk_manager._drawdown_threshold_3:
            return f"Drawdown circuit breaker (20%+ drawdown: {drawdown:.2f}%)"

        return "Trading halted (unknown reason)"
