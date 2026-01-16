"""
Scale-In Manager for active trade management.

This module implements the scale-in mechanism that adds to positions
as they move favorably to maximize winners.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from .trade_state import TradePosition


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ScaleInConfig:
    """
    Configuration for scale-in behavior.

    Attributes:
        first_trigger_r: Profit level for first scale-in (default: 1.0)
        first_scale_percent: Percentage to add at first trigger (default: 50)
        second_trigger_r: Profit level for second scale-in (default: 2.0)
        second_scale_percent: Percentage to add at second trigger (default: 25)
        max_scale_factor: Maximum total size as percentage of original (default: 200)
        min_trend_strength: Minimum trend strength for scale-in (default: 0.6)
        min_signal_quality: Minimum signal quality for scale-in (default: 0.7)
        enabled: Whether scale-in is enabled (default: True)
    """

    first_trigger_r: float = 1.0
    first_scale_percent: float = 50.0
    second_trigger_r: float = 2.0
    second_scale_percent: float = 25.0
    max_scale_factor: float = 200.0
    min_trend_strength: float = 0.6
    min_signal_quality: float = 0.7
    enabled: bool = True


@dataclass
class ScaleInOperation:
    """
    Record of a scale-in operation.

    Attributes:
        ticket: Original position ticket number
        new_ticket: Ticket number of the scaled-in position
        original_volume: Original position volume
        added_volume: Volume added in scale-in
        total_volume: Total volume after scale-in
        scale_percent: Percentage added as decimal (0.5 = 50%)
        trigger_price: Price at which scale-in was triggered
        fill_price: Price at which scale-in order was filled
        new_stop_loss: New weighted average stop loss
        old_stop_loss: Original stop loss
        reason: Reason for the scale-in
        timestamp: When the scale-in occurred
    """

    ticket: int
    new_ticket: int
    original_volume: float
    added_volume: float
    total_volume: float
    scale_percent: float
    trigger_price: float
    fill_price: float
    new_stop_loss: Optional[float]
    old_stop_loss: Optional[float]
    reason: str
    timestamp: float


@dataclass
class ScaleInPerformance:
    """
    Performance metrics for scale-in operations.

    Attributes:
        ticket: Position ticket number
        scaled_in_count: Number of times scaled in
        total_added_volume: Total volume added through scale-ins
        final_profit_r: Final profit in R multiples
        scale_in_profit_r: Profit contribution from scaled-in portion
        would_have_profit_r: Profit if no scale-in was done
        improvement_r: Improvement in R from scale-in
        timestamp: When the performance was recorded
    """

    ticket: int
    scaled_in_count: int
    total_added_volume: float
    final_profit_r: float
    scale_in_profit_r: float
    would_have_profit_r: float
    improvement_r: float
    timestamp: float


class ScaleInManager:
    """
    Manages scale-in operations for open positions.

    Features:
    - Adds 50% more position when trade reaches 1R profit (configurable)
    - Adds another 25% when trade reaches 2R profit (configurable)
    - Maximum total size: 200% of original (configurable)
    - Only scales in if trade is moving in favor (trend confirmation)
    - Only scales in if signal quality remains high
    - Calculates new SL for scaled position (weighted average)
    - Comprehensive logging of all operations
    - Performance tracking for scale-in effectiveness

    Usage:
        manager = ScaleInManager(mt5_connector)
        config = ScaleInConfig(first_trigger_r=1.0)

        # Check and execute scale-in for a position
        operation = await manager.check_scale_in_trigger(position, config)
        if operation:
            logger.info(f"Scaled in: added {operation.added_volume} lots")
    """

    def __init__(self, mt5_connector: Optional["MT5Connector"] = None):
        """
        Initialize the ScaleInManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
        """
        self._mt5 = mt5_connector
        self._operation_history: list[ScaleInOperation] = []
        self._performance_data: dict[int, ScaleInPerformance] = {}
        self._scale_in_triggers: dict[int, list[str]] = {}

        logger.info("ScaleInManager initialized")

    def _get_triggered_scales(self, ticket: int) -> list[str]:
        """
        Get list of scale-in triggers already executed for a position.

        Args:
            ticket: Position ticket number

        Returns:
            List of trigger names already executed
        """
        return self._scale_in_triggers.get(ticket, []).copy()

    def _mark_trigger_executed(self, ticket: int, trigger_name: str) -> None:
        """
        Mark a scale-in trigger as executed for a position.

        Args:
            ticket: Position ticket number
            trigger_name: Name of the trigger (e.g., "first", "second")
        """
        if ticket not in self._scale_in_triggers:
            self._scale_in_triggers[ticket] = []
        self._scale_in_triggers[ticket].append(trigger_name)
        logger.debug(
            f"Position {ticket} scale-in trigger '{trigger_name}' marked as executed"
        )

    def _clear_scale_in_tracking(self, ticket: int) -> None:
        """
        Clear scale-in tracking for a closed position.

        Args:
            ticket: Position ticket number
        """
        if ticket in self._scale_in_triggers:
            del self._scale_in_triggers[ticket]
            logger.debug(f"Position {ticket} scale-in tracking cleared")

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

    def _calculate_current_profit_r(self, position: TradePosition) -> float:
        """
        Calculate current profit in R multiples.

        Args:
            position: TradePosition

        Returns:
            Current profit as R multiple
        """
        initial_risk = self._calculate_initial_risk(position)

        if initial_risk == 0:
            return 0.0

        return position.profit / initial_risk

    def _calculate_total_scaled_volume(self, ticket: int) -> float:
        """
        Calculate total volume added through scale-ins for a position.

        Args:
            ticket: Position ticket number

        Returns:
            Total volume added
        """
        operations = [op for op in self._operation_history if op.ticket == ticket]
        return sum(op.added_volume for op in operations)

    def _check_max_scale_factor(
        self, position: TradePosition, added_volume: float, config: ScaleInConfig
    ) -> bool:
        """
        Check if scaling in would exceed maximum scale factor.

        Args:
            position: TradePosition
            added_volume: Volume to add
            config: ScaleInConfig

        Returns:
            True if within max scale factor, False otherwise
        """
        original_volume = position.volume
        total_scaled = self._calculate_total_scaled_volume(position.ticket)
        current_total = original_volume + total_scaled

        # Calculate new total after adding
        new_total = current_total + added_volume

        # Calculate scale factor
        scale_factor = (new_total / original_volume) * 100

        if scale_factor > config.max_scale_factor:
            logger.debug(
                f"Position {position.ticket} scale-in would exceed max scale factor: "
                f"{scale_factor:.1f}% > {config.max_scale_factor}%"
            )
            return False

        return True

    def _check_trend_confirmation(
        self, position: TradePosition, config: ScaleInConfig
    ) -> bool:
        """
        Check if trend confirmation conditions are met for scale-in.

        This verifies that the trade is moving in the expected direction
        based on price action and trend strength.

        Args:
            position: TradePosition
            config: ScaleInConfig

        Returns:
            True if trend confirms scale-in, False otherwise
        """
        # Get trend strength (placeholder - would use actual trend analysis)
        trend_strength = self._get_trend_strength(position)

        if trend_strength < config.min_trend_strength:
            logger.debug(
                f"Position {position.ticket} trend strength too low for scale-in: "
                f"{trend_strength:.2f} < {config.min_trend_strength}"
            )
            return False

        # Check price is moving in favor
        current_price = position.current_price
        entry_price = position.entry_price

        if position.direction == "BUY":
            # For LONG: price should be above entry
            if current_price <= entry_price:
                logger.debug(
                    f"Position {position.ticket} price not in favor: "
                    f"{current_price:.5f} <= {entry_price:.5f}"
                )
                return False
        else:  # SELL
            # For SHORT: price should be below entry
            if current_price >= entry_price:
                logger.debug(
                    f"Position {position.ticket} price not in favor: "
                    f"{current_price:.5f} >= {entry_price:.5f}"
                )
                return False

        logger.debug(
            f"Position {position.ticket} trend confirmed for scale-in: "
            f"strength={trend_strength:.2f}, price_in_favor=True"
        )
        return True

    def _get_trend_strength(self, position: TradePosition) -> float:
        """
        Get trend strength for a position.

        This is a placeholder that returns a default trend strength.
        In production, this would analyze price data, moving averages,
        RSI, ADX, or other trend indicators.

        Args:
            position: TradePosition

        Returns:
            Trend strength value (0.0 to 1.0)
        """
        # TODO: Implement actual trend strength calculation
        # For now, return a reasonable default based on profit
        profit_r = self._calculate_current_profit_r(position)

        # Simple heuristic: higher profit = stronger trend
        # Cap at 1.0
        trend_strength = min(0.5 + (profit_r * 0.2), 1.0)

        logger.debug(
            f"Using heuristic trend strength {trend_strength:.2f} for {position.symbol} "
            f"(profit: {profit_r:.2f}R). Real trend analysis not yet implemented."
        )

        return trend_strength

    def _check_signal_quality(
        self, position: TradePosition, config: ScaleInConfig
    ) -> bool:
        """
        Check if signal quality remains high enough for scale-in.

        This verifies that the original trading signal is still valid
        and market conditions haven't deteriorated.

        Args:
            position: TradePosition
            config: ScaleInConfig

        Returns:
            True if signal quality is sufficient, False otherwise
        """
        # Get signal quality (placeholder - would use actual signal analysis)
        signal_quality = self._get_signal_quality(position)

        if signal_quality < config.min_signal_quality:
            logger.debug(
                f"Position {position.ticket} signal quality too low for scale-in: "
                f"{signal_quality:.2f} < {config.min_signal_quality}"
            )
            return False

        logger.debug(
            f"Position {position.ticket} signal quality confirmed: {signal_quality:.2f}"
        )
        return True

    def _get_signal_quality(self, position: TradePosition) -> float:
        """
        Get signal quality for a position.

        This is a placeholder that returns a default signal quality.
        In production, this would analyze the original signal,
        market conditions, volatility, etc.

        Args:
            position: TradePosition

        Returns:
            Signal quality value (0.0 to 1.0)
        """
        # TODO: Implement actual signal quality calculation
        # For now, return a reasonable default
        default_quality = 0.8

        logger.debug(
            f"Using default signal quality {default_quality:.2f} for {position.symbol}. "
            f"Real signal quality analysis not yet implemented."
        )

        return default_quality

    def _calculate_weighted_average_sl(
        self, position: TradePosition, added_volume: float
    ) -> Optional[float]:
        """
        Calculate new weighted average stop loss for scaled position.

        The weighted average SL ensures that the combined position has
        a single stop loss that represents the average risk of all entries.

        Args:
            position: TradePosition
            added_volume: Volume being added

        Returns:
            New weighted average stop loss, or None if no SL exists
        """
        if position.stop_loss is None:
            return None

        # For scale-in, use the current SL (or entry) as SL for new position
        # Calculate weighted average: (volume1 * SL1 + volume2 * SL2) / (volume1 + volume2)
        original_volume = position.volume
        total_scaled = self._calculate_total_scaled_volume(position.ticket)
        current_total_volume = original_volume + total_scaled
        new_total_volume = current_total_volume + added_volume

        # New position uses same SL as current (usually breakeven or trailing)
        new_position_sl = position.stop_loss

        # Calculate weighted average
        weighted_sl = (
            (current_total_volume * position.stop_loss + added_volume * new_position_sl)
            / new_total_volume
        )

        logger.debug(
            f"Calculated weighted average SL: {weighted_sl:.5f} "
            f"(original: {position.stop_loss:.5f}, new: {new_position_sl:.5f})"
        )

        return weighted_sl

    async def check_scale_in_trigger(
        self, position: TradePosition, config: ScaleInConfig
    ) -> Optional[ScaleInOperation]:
        """
        Check and execute scale-in for a position if conditions are met.

        Scale-in logic:
        - Check if scale-in is enabled
        - Check which triggers have been executed (first, second)
        - Check if position has reached trigger profit level
        - Verify trend confirmation (price moving in favor)
        - Verify signal quality remains high
        - Check max scale factor not exceeded
        - Calculate volume to add
        - Execute scale-in order via MT5
        - Calculate new weighted average SL

        Args:
            position: TradePosition to check
            config: ScaleInConfig with parameters

        Returns:
            ScaleInOperation if scale-in was executed, None otherwise
        """
        if not config.enabled:
            logger.debug(f"Scale-in disabled for position {position.ticket}")
            return None

        # Get current profit in R
        current_profit_r = self._calculate_current_profit_r(position)

        if current_profit_r <= 0:
            logger.debug(
                f"Position {position.ticket} not profitable, skipping scale-in check"
            )
            return None

        # Check which triggers have been executed
        executed_triggers = self._get_triggered_scales(position.ticket)

        # Determine which trigger to check
        # Use small tolerance to handle floating point precision issues
        tolerance = 1e-9
        trigger_name = None
        trigger_r = 0.0
        scale_percent = 0.0

        if "first" not in executed_triggers and current_profit_r >= config.first_trigger_r - tolerance:
            trigger_name = "first"
            trigger_r = config.first_trigger_r
            scale_percent = config.first_scale_percent
        elif "second" not in executed_triggers and current_profit_r >= config.second_trigger_r - tolerance:
            trigger_name = "second"
            trigger_r = config.second_trigger_r
            scale_percent = config.second_scale_percent
        else:
            logger.debug(
                f"Position {position.ticket} no scale-in trigger met: "
                f"profit={current_profit_r:.2f}R, executed={executed_triggers}"
            )
            return None

        # Check trend confirmation
        if not self._check_trend_confirmation(position, config):
            logger.debug(
                f"Position {position.ticket} trend not confirmed, skipping scale-in"
            )
            return None

        # Check signal quality
        if not self._check_signal_quality(position, config):
            logger.debug(
                f"Position {position.ticket} signal quality insufficient, skipping scale-in"
            )
            return None

        # Calculate volume to add
        original_volume = position.volume
        added_volume = original_volume * (scale_percent / 100)

        # Check max scale factor
        if not self._check_max_scale_factor(position, added_volume, config):
            logger.debug(
                f"Position {position.ticket} max scale factor exceeded, skipping scale-in"
            )
            return None

        # Execute scale-in order via MT5
        if self._mt5 is not None:
            new_ticket = await self._execute_scale_in_order(
                position, added_volume, trigger_name
            )
        else:
            # For testing, generate a fake ticket
            new_ticket = position.ticket + 1000 + len(executed_triggers)
            logger.debug(
                f"MT5 connector not configured, would execute scale-in order (ticket: {new_ticket})"
            )

        # Calculate new weighted average SL
        old_sl = position.stop_loss
        new_sl = self._calculate_weighted_average_sl(position, added_volume)

        # Create operation record
        operation = ScaleInOperation(
            ticket=position.ticket,
            new_ticket=new_ticket,
            original_volume=original_volume,
            added_volume=added_volume,
            total_volume=original_volume + added_volume,
            scale_percent=scale_percent / 100,
            trigger_price=position.current_price,
            fill_price=position.current_price,  # In production, get actual fill price
            new_stop_loss=new_sl,
            old_stop_loss=old_sl,
            reason=self._get_scale_in_reason(trigger_name, current_profit_r),
            timestamp=position.get_trade_age_seconds(),
        )

        # Log the operation
        logger.info(
            f"Scale-in executed for position {position.ticket} ({position.symbol} {position.direction}): "
            f"+{scale_percent:.0f}% ({added_volume:.2f} lots) "
            f"| Price: {position.current_price:.5f} "
            f"| Profit: {current_profit_r:.2f}R "
            f"| SL: {old_sl:.5f} -> {new_sl:.5f} "
            f"| New ticket: {new_ticket}"
        )

        # Mark trigger as executed
        self._mark_trigger_executed(position.ticket, trigger_name)

        # Store operation in history
        self._operation_history.append(operation)

        return operation

    async def _execute_scale_in_order(
        self, position: TradePosition, volume: float, trigger_name: str
    ) -> int:
        """
        Execute scale-in order via MT5.

        Args:
            position: TradePosition to scale in
            volume: Volume to add
            trigger_name: Name of the trigger

        Returns:
            Ticket number of the new position

        Raises:
            ConnectionError: If MT5 order fails
        """
        if self._mt5 is None:
            raise ConnectionError("MT5 connector not configured")

        try:
            # Determine order type
            order_type = 0  # BUY
            if position.direction == "SELL":
                order_type = 1  # SELL

            # Call the MT5 API to place order
            new_ticket = await self._mt5.place_order(
                symbol=position.symbol,
                order_type=order_type,
                volume=volume,
                price=position.current_price,
                sl=position.stop_loss,
                tp=position.take_profit,
                comment=f"scale_in_{trigger_name}",
            )

            logger.info(
                f"MT5 scale-in order executed for position {position.ticket}: "
                f"new ticket {new_ticket}"
            )

            return new_ticket

        except Exception as e:
            logger.error(f"Failed to execute scale-in order via MT5: {e}")
            raise ConnectionError(f"MT5 scale-in order failed: {e}") from e

    def _get_scale_in_reason(self, trigger_name: str, current_profit_r: float) -> str:
        """
        Get a human-readable reason for the scale-in.

        Args:
            trigger_name: Name of the trigger (first, second)
            current_profit_r: Current profit in R multiples

        Returns:
            Reason string
        """
        return (
            f"Scale-in triggered at {trigger_name} level "
            f"(profit: {current_profit_r:.2f}R), trend confirmed"
        )

    def record_performance(
        self,
        ticket: int,
        final_profit_r: float,
        scale_in_profit_r: float,
        would_have_profit_r: float,
    ) -> None:
        """
        Record performance metrics for a position that used scale-in.

        Args:
            ticket: Position ticket number
            final_profit_r: Final profit in R multiples (with scale-in)
            scale_in_profit_r: Profit contribution from scaled-in portion
            would_have_profit_r: Profit if no scale-in was done
        """
        operations = [op for op in self._operation_history if op.ticket == ticket]
        total_added_volume = sum(op.added_volume for op in operations)

        improvement_r = final_profit_r - would_have_profit_r

        performance = ScaleInPerformance(
            ticket=ticket,
            scaled_in_count=len(operations),
            total_added_volume=total_added_volume,
            final_profit_r=final_profit_r,
            scale_in_profit_r=scale_in_profit_r,
            would_have_profit_r=would_have_profit_r,
            improvement_r=improvement_r,
            timestamp=datetime.utcnow().timestamp(),
        )

        self._performance_data[ticket] = performance

        logger.info(
            f"Scale-in performance recorded for position {ticket}: "
            f"scaled_in={len(operations)}x, "
            f"final_profit={final_profit_r:.2f}R, "
            f"would_have={would_have_profit_r:.2f}R, "
            f"improvement={improvement_r:.2f}R"
        )

    def get_operation_history(self, ticket: Optional[int] = None) -> list[ScaleInOperation]:
        """
        Get scale-in operation history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of ScaleInOperation records
        """
        if ticket is None:
            return self._operation_history.copy()
        return [op for op in self._operation_history if op.ticket == ticket]

    def get_performance_data(self, ticket: int) -> Optional[ScaleInPerformance]:
        """
        Get performance data for a position.

        Args:
            ticket: Position ticket number

        Returns:
            ScaleInPerformance if found, None otherwise
        """
        return self._performance_data.get(ticket)

    def get_all_performance_data(self) -> list[ScaleInPerformance]:
        """
        Get all performance data.

        Returns:
            List of ScaleInPerformance records
        """
        return list(self._performance_data.values())

    def clear_operation_history(self) -> None:
        """Clear the scale-in operation history."""
        self._operation_history.clear()
        logger.debug("Scale-in operation history cleared")

    def clear_performance_data(self, ticket: Optional[int] = None) -> None:
        """
        Clear performance data.

        Args:
            ticket: Optional ticket number to clear. If None, clears all.
        """
        if ticket is None:
            self._performance_data.clear()
            logger.debug("All scale-in performance data cleared")
        elif ticket in self._performance_data:
            del self._performance_data[ticket]
            logger.debug(f"Scale-in performance data cleared for position {ticket}")
