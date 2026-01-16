"""
Holding Time Optimizer for active trade management.

This module implements the holding time optimization mechanism that closes
trades that have been open too long without reaching their targets.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .trade_state import TradePosition, TradeState


# Configure logging
logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types for holding time limits."""

    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"


@dataclass
class HoldingTimeConfig:
    """
    Configuration for holding time optimization behavior.

    Attributes:
        trending_max_hours: Maximum holding time in hours for trending regime (default: 4)
        ranging_max_hours: Maximum holding time in hours for ranging regime (default: 2)
        volatile_max_hours: Maximum holding time in hours for volatile regime (default: 1)
        default_regime: Default regime to use if none specified (default: RANGING)
        close_percentage_at_limit: Percentage to close when limit reached (default: 0.5)
        enabled: Whether holding time optimization is enabled (default: True)
    """

    trending_max_hours: float = 4.0
    ranging_max_hours: float = 2.0
    volatile_max_hours: float = 1.0
    default_regime: MarketRegime = MarketRegime.RANGING
    close_percentage_at_limit: float = 0.5  # Close 50% at limit
    enabled: bool = True


@dataclass
class HoldingTimeUpdate:
    """
    Record of a holding time close.

    Attributes:
        ticket: Position ticket number
        trade_age_seconds: Age of trade when closed
        max_allowed_seconds: Maximum allowed age for this regime
        closed_lots: Number of lots closed
        remaining_lots: Number of lots remaining
        close_price: Price at which position was closed
        profit_at_close: Profit in currency units at time of close
        was_profitable: Whether position was profitable when closed
        close_percentage: Percentage of position closed (0.0 to 1.0)
        regime: Market regime used for this decision
        reason: Reason for the close
        timestamp: When the close occurred
    """

    ticket: int
    trade_age_seconds: int
    max_allowed_seconds: int
    closed_lots: float
    remaining_lots: float
    close_price: float
    profit_at_close: float
    was_profitable: bool
    close_percentage: float
    regime: MarketRegime
    reason: str
    timestamp: float


class HoldingTimeOptimizer:
    """
    Manages holding time optimization for open positions.

    Features:
    - Configurable maximum holding times by market regime:
      * Trending regime: max 4 hours
      * Ranging regime: max 2 hours
      * Volatile regime: max 1 hour
    - Checks holding time limit for each position
    - Closes 50% position when limit exceeded (if profitable)
    - Closes entire position if very old (> 2x limit)
    - Closes entire position immediately if losing
    - Tracks holding time statistics in database
    - Comprehensive logging of all operations

    Usage:
        optimizer = HoldingTimeOptimizer(mt5_connector)
        config = HoldingTimeConfig(ranging_max_hours=2.0)

        # Check and execute holding time close for a position
        update = await optimizer.check_holding_time_limit(position, config, regime)
        if update:
            logger.info(f"Holding time close: {update.close_percentage*100}%")
    """

    def __init__(
        self,
        mt5_connector: Optional["MT5Connector"] = None,
        alert_system: Optional["ManagementAlertSystem"] = None,
    ):
        """
        Initialize the HoldingTimeOptimizer.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
            alert_system: ManagementAlertSystem instance for sending alerts
        """
        self._mt5 = mt5_connector
        self._alert_system = alert_system
        self._close_history: list[HoldingTimeUpdate] = []
        self._last_check_time: dict[int, float] = {}  # ticket -> timestamp

        logger.info("HoldingTimeOptimizer initialized")

    def get_max_holding_time_seconds(self, config: HoldingTimeConfig, regime: MarketRegime) -> int:
        """
        Get maximum holding time in seconds for a given regime.

        Args:
            config: HoldingTimeConfig with parameters
            regime: MarketRegime to get limit for

        Returns:
            Maximum holding time in seconds
        """
        if regime == MarketRegime.TRENDING:
            return int(config.trending_max_hours * 3600)
        elif regime == MarketRegime.RANGING:
            return int(config.ranging_max_hours * 3600)
        elif regime == MarketRegime.VOLATILE:
            return int(config.volatile_max_hours * 3600)
        else:
            # Default to ranging regime
            return int(config.ranging_max_hours * 3600)

    def _is_position_profitable(self, position: TradePosition) -> bool:
        """
        Check if a position is currently profitable.

        Args:
            position: TradePosition to check

        Returns:
            True if position has positive profit
        """
        total_pnl = position.profit + position.swap + position.commission
        return total_pnl > 0

    async def check_holding_time_limit(
        self,
        position: TradePosition,
        config: HoldingTimeConfig,
        regime: Optional[MarketRegime] = None
    ) -> Optional[HoldingTimeUpdate]:
        """
        Check and execute holding time closes for a position.

        Holding time logic:
        - Check if holding time optimization is enabled
        - Calculate trade age (current_time - entry_time)
        - Check if trade is profitable (if losing, cut immediately)
        - Get maximum holding time for regime
        - If age exceeds limit: close 50% position
        - If very old (> 2x limit): close entire position

        Args:
            position: TradePosition to check
            config: HoldingTimeConfig with parameters
            regime: MarketRegime (uses default if None)

        Returns:
            HoldingTimeUpdate if position was closed, None otherwise
        """
        if not config.enabled:
            logger.debug(f"Holding time optimization disabled for position {position.ticket}")
            return None

        # Use default regime if not specified
        if regime is None:
            regime = config.default_regime

        # Calculate trade age
        trade_age_seconds = position.get_trade_age_seconds()

        # Get maximum holding time for this regime
        max_allowed_seconds = self.get_max_holding_time_seconds(config, regime)

        # Check if position is profitable
        is_profitable = self._is_position_profitable(position)

        # Determine if we need to close and how much
        close_percentage, reason = self._determine_close_action(
            trade_age_seconds, max_allowed_seconds, is_profitable
        )

        if close_percentage <= 0:
            logger.debug(
                f"Position {position.ticket} holding time check: "
                f"{trade_age_seconds}s / {max_allowed_seconds}s, no action needed"
            )
            return None

        # Execute the close
        return await self._execute_holding_time_close(
            position, close_percentage, reason, regime, trade_age_seconds, max_allowed_seconds
        )

    def _determine_close_action(
        self, trade_age_seconds: int, max_allowed_seconds: int, is_profitable: bool
    ) -> tuple[float, str]:
        """
        Determine what close action to take based on age and profitability.

        Args:
            trade_age_seconds: Current age of trade in seconds
            max_allowed_seconds: Maximum allowed age in seconds
            is_profitable: Whether position is profitable

        Returns:
            Tuple of (close_percentage, reason)
        """
        # If losing, close entire position immediately
        if not is_profitable:
            return 1.0, "Losing position, closing immediately"

        # If very old (> 2x limit), close entire position
        if trade_age_seconds > max_allowed_seconds * 2:
            return 1.0, f"Position very old ({trade_age_seconds}s > 2x {max_allowed_seconds}s)"

        # If at or past limit, close partial (50%)
        if trade_age_seconds >= max_allowed_seconds:
            return 0.5, f"Position at holding time limit ({trade_age_seconds}s >= {max_allowed_seconds}s)"

        # No action needed
        return 0.0, ""

    async def _execute_holding_time_close(
        self,
        position: TradePosition,
        close_percentage: float,
        reason: str,
        regime: MarketRegime,
        trade_age_seconds: int,
        max_allowed_seconds: int,
    ) -> Optional[HoldingTimeUpdate]:
        """
        Execute a holding time close for a position.

        Args:
            position: TradePosition to close
            close_percentage: Percentage of position to close (0.0 to 1.0)
            reason: Reason for the close
            regime: MarketRegime used for this decision
            trade_age_seconds: Age of trade when closed
            max_allowed_seconds: Maximum allowed age for this regime

        Returns:
            HoldingTimeUpdate if successful, None otherwise
        """
        # Calculate lots to close
        lots_to_close = position.volume * close_percentage
        lots_remaining = position.volume - lots_to_close

        # Validate we're not closing more than we have
        if lots_to_close > position.volume:
            logger.error(
                f"Attempting to close {lots_to_close} lots but only have {position.volume}"
            )
            return None

        # Calculate total PnL at close
        profit_at_close = position.profit + position.swap + position.commission

        # Send close order to MT5
        if self._mt5 is not None:
            close_price = await self._send_holding_time_close_to_mt5(
                position, lots_to_close
            )
            if close_price is None:
                logger.error(f"Failed to close position {position.ticket} due to holding time")
                return None
        else:
            logger.debug(
                f"MT5 connector not configured, would close {lots_to_close} lots"
            )
            close_price = position.current_price

        # Create update record
        update = HoldingTimeUpdate(
            ticket=position.ticket,
            trade_age_seconds=trade_age_seconds,
            max_allowed_seconds=max_allowed_seconds,
            closed_lots=lots_to_close,
            remaining_lots=lots_remaining,
            close_price=close_price,
            profit_at_close=profit_at_close,
            was_profitable=profit_at_close > 0,
            close_percentage=close_percentage,
            regime=regime,
            reason=reason,
            timestamp=position.get_trade_age_seconds(),
        )

        # Log the close
        logger.info(
            f"Holding time close for position {position.ticket} ({position.symbol} {position.direction}): "
            f"{close_percentage*100:.1f}% ({lots_to_close:.2f} lots) "
            f"| Age: {trade_age_seconds}s (max: {max_allowed_seconds}s) "
            f"| Regime: {regime.value} "
            f"| Price: {close_price:.5f} "
            f"| PnL: {profit_at_close:.2f} "
            f"| Reason: {reason} "
            f"| Remaining: {lots_remaining:.2f} lots"
        )

        # Store update in history
        self._close_history.append(update)

        # Send alert if alert system is configured
        if self._alert_system is not None:
            try:
                import asyncio
                action_taken = f"closed_{close_percentage*100:.0f}%"
                asyncio.create_task(
                    self._alert_system.alert_holding_limit_reached(
                        ticket=position.ticket,
                        symbol=position.symbol,
                        hold_duration_seconds=update.trade_age_seconds,
                        max_hold_duration_seconds=update.max_allowed_seconds,
                        current_profit=position.profit,
                        action_taken=action_taken,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send holding limit alert: {e}")

        # Update position state if fully closed
        if close_percentage >= 1.0:
            position.transition_state(
                TradeState.CLOSED, reason=f"Holding time limit: {reason}"
            )
        elif position.state == TradeState.OPEN:
            position.transition_state(
                TradeState.PARTIAL, reason=f"Partial holding time close: {reason}"
            )

        # Update position volume
        position.volume = lots_remaining

        return update

    async def _send_holding_time_close_to_mt5(
        self, position: TradePosition, lots: float
    ) -> Optional[float]:
        """
        Send holding time close order to MT5.

        Args:
            position: TradePosition to close
            lots: Number of lots to close

        Returns:
            Close price if successful, None otherwise

        Raises:
            ConnectionError: If MT5 close fails
        """
        if self._mt5 is None:
            logger.debug(
                f"MT5 connector not configured, skipping holding time close for position {position.ticket}"
            )
            return None

        try:
            # Call the MT5 API to close position
            close_price = await self._mt5.close_position(
                ticket=position.ticket,
                lots=lots,
            )
            logger.debug(
                f"MT5 holding time close sent for position {position.ticket}: "
                f"{lots} lots at {close_price:.5f}"
            )
            return close_price
        except Exception as e:
            logger.error(f"Failed to send holding time close to MT5: {e}")
            raise ConnectionError(f"MT5 holding time close failed: {e}") from e

    def get_close_history(self, ticket: Optional[int] = None) -> list[HoldingTimeUpdate]:
        """
        Get holding time close history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of HoldingTimeUpdate records
        """
        if ticket is None:
            return self._close_history.copy()
        return [c for c in self._close_history if c.ticket == ticket]

    def clear_close_history(self) -> None:
        """Clear the holding time close history."""
        self._close_history.clear()
        self._last_check_time.clear()
        logger.debug("Holding time close history cleared")

    def get_statistics(self) -> dict:
        """
        Get statistics on holding time optimization.

        Returns:
            Dictionary with statistics including:
            - total_closes: Total number of holding time closes
            - profitable_closes: Number of closes that were profitable
            - losing_closes: Number of closes that were losing
            - average_holding_time: Average holding time before close (seconds)
            - by_regime: Breakdown by market regime
        """
        if not self._close_history:
            return {
                "total_closes": 0,
                "profitable_closes": 0,
                "losing_closes": 0,
                "average_holding_time": 0,
                "by_regime": {},
            }

        total_closes = len(self._close_history)
        profitable_closes = sum(1 for c in self._close_history if c.was_profitable)
        losing_closes = total_closes - profitable_closes
        average_holding_time = sum(c.trade_age_seconds for c in self._close_history) / total_closes

        # Breakdown by regime
        by_regime = {}
        for regime in MarketRegime:
            regime_closes = [c for c in self._close_history if c.regime == regime]
            if regime_closes:
                by_regime[regime.value] = {
                    "count": len(regime_closes),
                    "profitable": sum(1 for c in regime_closes if c.was_profitable),
                    "losing": sum(1 for c in regime_closes if not c.was_profitable),
                    "avg_holding_time": sum(c.trade_age_seconds for c in regime_closes) / len(regime_closes),
                }

        return {
            "total_closes": total_closes,
            "profitable_closes": profitable_closes,
            "losing_closes": losing_closes,
            "average_holding_time": average_holding_time,
            "by_regime": by_regime,
        }
