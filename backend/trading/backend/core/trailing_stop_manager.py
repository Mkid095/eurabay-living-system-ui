"""
Trailing Stop Manager for active trade management.

This module implements the trailing stop mechanism that moves stop losses
as price moves favorably to protect profits.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .trade_state import TradePosition


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class TrailingStopConfig:
    """
    Configuration for trailing stop behavior.

    Attributes:
        atr_multiplier: ATR multiplier for trail distance (default: 2.0)
        atr_period: Period for ATR calculation (default: 14)
        min_profit_r: Minimum profit in R multiples before trailing starts (default: 1.0)
        trail_step_atr_multiplier: ATR multiplier for minimum step (default: 0.5)
        enabled: Whether trailing stop is enabled (default: True)
    """

    atr_multiplier: float = 2.0
    atr_period: int = 14
    min_profit_r: float = 1.0
    trail_step_atr_multiplier: float = 0.5
    enabled: bool = True


@dataclass
class TrailingStopUpdate:
    """
    Record of a trailing stop update.

    Attributes:
        ticket: Position ticket number
        old_stop_loss: Previous stop loss value
        new_stop_loss: New stop loss value
        current_price: Price at time of update
        trail_distance: Distance from price to new SL
        reason: Reason for the update
        timestamp: When the update occurred
    """

    ticket: int
    old_stop_loss: Optional[float]
    new_stop_loss: float
    current_price: float
    trail_distance: float
    reason: str
    timestamp: float


class TrailingStopManager:
    """
    Manages trailing stop losses for open positions.

    Features:
    - ATR-based trail distance calculation
    - Direction-aware trailing (LONG vs SHORT)
    - Minimum profit requirement before trailing starts
    - Trail step to avoid too frequent updates
    - Never moves SL against position (only locks in profits)
    - Comprehensive logging of all updates

    Usage:
        manager = TrailingStopManager(mt5_connector)
        config = TrailingStopConfig(atr_multiplier=2.0)

        # Check and update trailing stop for a position
        update = await manager.update_trailing_stop(position, config)
        if update:
            logger.info(f"Trailing stop updated: {update.new_stop_loss}")
    """

    def __init__(self, mt5_connector: Optional["MT5Connector"] = None):
        """
        Initialize the TrailingStopManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
        """
        self._mt5 = mt5_connector
        self._update_history: list[TrailingStopUpdate] = []

        logger.info("TrailingStopManager initialized")

    def calculate_trail_distance(
        self, position: TradePosition, config: TrailingStopConfig
    ) -> float:
        """
        Calculate the trailing stop distance based on ATR.

        The trail distance is calculated as: atr_multiplier * ATR
        Default is 2x ATR, but this is configurable.

        Args:
            position: TradePosition to calculate for
            config: TrailingStopConfig with parameters

        Returns:
            Trail distance in price units
        """
        # Get ATR value (placeholder - will be replaced with actual ATR calculation)
        atr = self._get_atr_value(position.symbol, config.atr_period)

        # Calculate trail distance
        trail_distance = atr * config.atr_multiplier

        logger.debug(
            f"Calculated trail distance for {position.symbol}: {trail_distance:.5f} "
            f"(ATR: {atr:.5f}, multiplier: {config.atr_multiplier})"
        )

        return trail_distance

    def _get_atr_value(self, symbol: str, period: int) -> float:
        """
        Get ATR value for a symbol.

        This is a placeholder that returns a default ATR value.
        In production, this would calculate the actual ATR from price data.

        Args:
            symbol: Trading symbol
            period: ATR period

        Returns:
            ATR value (default 0.0010 for forex pairs)
        """
        # TODO: Implement actual ATR calculation from price data
        # For now, return a reasonable default for forex pairs
        default_atr = 0.0010  # 10 pips for EURUSD and similar pairs

        logger.debug(
            f"Using default ATR value {default_atr:.5f} for {symbol} "
            f"(period: {period}). Real ATR calculation not yet implemented."
        )

        return default_atr

    async def update_trailing_stop(
        self, position: TradePosition, config: TrailingStopConfig
    ) -> Optional[TrailingStopUpdate]:
        """
        Update trailing stop for a position if conditions are met.

        Trailing stop logic:
        - For LONG positions:
          - Move SL up when price > entry + trail_distance
          - New SL = max(current_SL, price - trail_distance)
          - Never move SL down (only lock in profits)
        - For SHORT positions:
          - Move SL down when price < entry - trail_distance
          - New SL = min(current_SL, price + trail_distance)
          - Never move SL up (only lock in profits)

        Additional constraints:
        - Must be at least min_profit_r in profit before trailing starts
        - Must move by at least trail_step before updating

        Args:
            position: TradePosition to update
            config: TrailingStopConfig with parameters

        Returns:
            TrailingStopUpdate if SL was updated, None otherwise
        """
        if not config.enabled:
            logger.debug(f"Trailing stop disabled for position {position.ticket}")
            return None

        # Check if position has a stop loss
        if position.stop_loss is None:
            logger.debug(f"Position {position.ticket} has no stop loss, skipping")
            return None

        # Calculate trail distance
        trail_distance = self.calculate_trail_distance(position, config)
        trail_step = trail_distance * 0.5  # Default trail step is 0.5x trail distance

        # Calculate initial risk (entry - SL for LONG, SL - entry for SHORT)
        initial_risk = self._calculate_initial_risk(position)

        # Check minimum profit requirement
        # Use small tolerance to handle floating point precision issues
        tolerance = 1e-9
        current_profit_r = position.profit / initial_risk if initial_risk > 0 else 0

        if current_profit_r < config.min_profit_r - tolerance:
            logger.debug(
                f"Position {position.ticket} not at minimum profit yet: "
                f"{current_profit_r:.2f}R < {config.min_profit_r}R"
            )
            return None

        # Calculate new stop loss based on direction
        new_sl = self._calculate_new_sl(
            position, trail_distance, trail_step, config
        )

        # Check if SL should be updated
        if new_sl is None:
            logger.debug(f"Position {position.ticket} trailing stop not triggered")
            return None

        # Verify new SL is better than current SL (only lock in profits)
        if not self._is_sl_improvement(position, new_sl):
            logger.debug(
                f"New SL {new_sl:.5f} would not improve current SL "
                f"{position.stop_loss:.5f}, skipping update"
            )
            return None

        # Send update to MT5
        if self._mt5 is not None:
            await self._send_sl_update_to_mt5(position, new_sl)
        else:
            logger.debug(
                f"MT5 connector not configured, would update SL to {new_sl:.5f}"
            )

        # Create update record
        update = TrailingStopUpdate(
            ticket=position.ticket,
            old_stop_loss=position.stop_loss,
            new_stop_loss=new_sl,
            current_price=position.current_price,
            trail_distance=trail_distance,
            reason=self._get_update_reason(position, new_sl),
            timestamp=position.get_trade_age_seconds(),
        )

        # Log the update
        logger.info(
            f"Trailing stop updated for position {position.ticket} ({position.symbol} {position.direction}): "
            f"SL {position.stop_loss:.5f} -> {new_sl:.5f} "
            f"| Price: {position.current_price:.5f} "
            f"| Trail distance: {trail_distance:.5f} "
            f"| Profit: {position.profit:.2f}"
        )

        # Update position stop loss
        position.stop_loss = new_sl

        # Store update in history
        self._update_history.append(update)

        return update

    def _calculate_initial_risk(self, position: TradePosition) -> float:
        """
        Calculate the initial risk for a position.

        Args:
            position: TradePosition

        Returns:
            Initial risk in currency units
        """
        if position.stop_loss is None:
            return 0.0

        if position.direction == "BUY":
            return abs(position.entry_price - position.stop_loss) * position.volume * 100000
        else:  # SELL
            return abs(position.stop_loss - position.entry_price) * position.volume * 100000

    def _calculate_new_sl(
        self,
        position: TradePosition,
        trail_distance: float,
        trail_step: float,
        config: TrailingStopConfig,
    ) -> Optional[float]:
        """
        Calculate new stop loss based on position direction and current price.

        Args:
            position: TradePosition
            trail_distance: Distance from price to trail
            trail_step: Minimum step before updating
            config: TrailingStopConfig

        Returns:
            New stop loss value, or None if no update needed
        """
        current_price = position.current_price
        current_sl = position.stop_loss
        entry_price = position.entry_price

        if position.direction == "BUY":
            # For LONG positions
            # Check if price has moved enough to trigger trailing
            if current_price <= entry_price + trail_distance:
                return None

            # Calculate new SL: price - trail_distance
            potential_new_sl = current_price - trail_distance

            # Check if movement is at least trail_step
            if abs(potential_new_sl - current_sl) < trail_step:
                return None

            # Only update if new SL is higher (locks in more profit)
            if potential_new_sl <= current_sl:
                return None

            return potential_new_sl

        else:  # SELL
            # For SHORT positions
            # Check if price has moved enough to trigger trailing
            if current_price >= entry_price - trail_distance:
                return None

            # Calculate new SL: price + trail_distance
            potential_new_sl = current_price + trail_distance

            # Check if movement is at least trail_step
            if abs(potential_new_sl - current_sl) < trail_step:
                return None

            # Only update if new SL is lower (locks in more profit)
            if potential_new_sl >= current_sl:
                return None

            return potential_new_sl

    def _is_sl_improvement(self, position: TradePosition, new_sl: float) -> bool:
        """
        Check if new stop loss is an improvement (only locks in profits).

        For LONG: new SL must be higher than current SL
        For SHORT: new SL must be lower than current SL

        Args:
            position: TradePosition
            new_sl: Proposed new stop loss

        Returns:
            True if new SL is an improvement
        """
        if position.stop_loss is None:
            return True

        if position.direction == "BUY":
            return new_sl > position.stop_loss
        else:  # SELL
            return new_sl < position.stop_loss

    def _get_update_reason(self, position: TradePosition, new_sl: float) -> str:
        """
        Get a human-readable reason for the trailing stop update.

        Args:
            position: TradePosition
            new_sl: New stop loss value

        Returns:
            Reason string
        """
        if position.direction == "BUY":
            return f"Price moved up, SL raised to lock in profits"
        else:
            return f"Price moved down, SL lowered to lock in profits"

    async def _send_sl_update_to_mt5(
        self, position: TradePosition, new_sl: float
    ) -> None:
        """
        Send stop loss update to MT5.

        Args:
            position: TradePosition to update
            new_sl: New stop loss value

        Raises:
            ConnectionError: If MT5 update fails
        """
        if self._mt5 is None:
            logger.debug(
                f"MT5 connector not configured, skipping SL update for position {position.ticket}"
            )
            return

        try:
            # Call the MT5 API to update stop loss
            await self._mt5.update_stop_loss(position.ticket, new_sl)
            logger.debug(
                f"MT5 SL update sent for position {position.ticket}: {new_sl:.5f}"
            )
        except Exception as e:
            logger.error(f"Failed to send SL update to MT5: {e}")
            raise ConnectionError(f"MT5 SL update failed: {e}") from e

    def get_update_history(self, ticket: Optional[int] = None) -> list[TrailingStopUpdate]:
        """
        Get trailing stop update history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of TrailingStopUpdate records
        """
        if ticket is None:
            return self._update_history.copy()
        return [u for u in self._update_history if u.ticket == ticket]

    def clear_update_history(self) -> None:
        """Clear the trailing stop update history."""
        self._update_history.clear()
        logger.debug("Trailing stop update history cleared")
