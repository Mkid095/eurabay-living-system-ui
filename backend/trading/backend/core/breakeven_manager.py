"""
Breakeven Manager for active trade management.

This module implements the breakeven mechanism that moves stop losses
to breakeven when trades are sufficiently profitable to prevent losses.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .trade_state import TradePosition


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class BreakevenConfig:
    """
    Configuration for breakeven behavior.

    Attributes:
        profit_trigger_r: Profit in R multiples to trigger breakeven (default: 1.5)
        buffer_pips: Buffer in pips to move SL past entry (default: 2.0)
        cooldown_seconds: Cooldown period after entry before enabling (default: 300)
        enabled: Whether breakeven is enabled (default: True)
    """

    profit_trigger_r: float = 1.5
    buffer_pips: float = 2.0
    cooldown_seconds: int = 300  # 5 minutes
    enabled: bool = True


@dataclass
class BreakevenUpdate:
    """
    Record of a breakeven update.

    Attributes:
        ticket: Position ticket number
        old_stop_loss: Previous stop loss value
        new_stop_loss: New stop loss value (breakeven level)
        current_price: Price at time of update
        profit_r: Current profit in R multiples
        reason: Reason for the update
        timestamp: When the update occurred
    """

    ticket: int
    old_stop_loss: Optional[float]
    new_stop_loss: float
    current_price: float
    profit_r: float
    reason: str
    timestamp: float


class BreakevenManager:
    """
    Manages breakeven stop losses for open positions.

    Features:
    - Triggers when position reaches 1.5R profit (configurable)
    - Moves SL to entry price + spread (buffer)
    - Implements breakeven buffer (default 2 pips past entry)
    - Implements breakeven lock (never moves SL back from breakeven)
    - Implements breakeven cooldown (default 5 minutes after entry)
    - Comprehensive logging of all operations

    Usage:
        manager = BreakevenManager(mt5_connector)
        config = BreakevenConfig(profit_trigger_r=1.5)

        # Check and update breakeven for a position
        update = await manager.check_breakeven_trigger(position, config)
        if update:
            logger.info(f"Breakeven triggered: {update.new_stop_loss}")
    """

    def __init__(
        self,
        mt5_connector: Optional["MT5Connector"] = None,
        alert_system: Optional["ManagementAlertSystem"] = None,
    ):
        """
        Initialize the BreakevenManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
            alert_system: ManagementAlertSystem instance for sending alerts
        """
        self._mt5 = mt5_connector
        self._alert_system = alert_system
        self._update_history: list[BreakevenUpdate] = []
        self._breakeven_locked: set[int] = set()  # Positions locked at breakeven

        logger.info("BreakevenManager initialized")

    def calculate_breakeven_price(
        self, position: TradePosition, config: BreakevenConfig
    ) -> float:
        """
        Calculate the breakeven price for a position.

        The breakeven price is the entry price plus a small buffer
        to account for spread and commissions.

        Args:
            position: TradePosition to calculate for
            config: BreakevenConfig with parameters

        Returns:
            Breakeven price level
        """
        # Convert pips to price units
        # For most forex pairs, 1 pip = 0.0001
        pip_value = 0.0001
        buffer_price = config.buffer_pips * pip_value

        if position.direction == "BUY":
            # For LONG positions, breakeven is above entry
            breakeven_price = position.entry_price + buffer_price
        else:
            # For SHORT positions, breakeven is below entry
            breakeven_price = position.entry_price - buffer_price

        logger.debug(
            f"Calculated breakeven price for {position.symbol}: {breakeven_price:.5f} "
            f"(entry: {position.entry_price:.5f}, buffer: {buffer_price:.5f})"
        )

        return breakeven_price

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
        else:
            return abs(position.stop_loss - position.entry_price) * position.volume * 100000

    def _is_breakeven_locked(self, position: TradePosition) -> bool:
        """
        Check if a position is locked at breakeven.

        Once breakeven is triggered, the SL should never be moved back.

        Args:
            position: TradePosition to check

        Returns:
            True if position is locked at breakeven
        """
        return position.ticket in self._breakeven_locked

    def _is_cooldown_active(self, position: TradePosition, config: BreakevenConfig) -> bool:
        """
        Check if breakeven cooldown is still active.

        Breakeven should not be triggered until a cooldown period
        has passed since entry (default 5 minutes).

        Args:
            position: TradePosition to check
            config: BreakevenConfig with cooldown parameters

        Returns:
            True if cooldown is still active
        """
        trade_age_seconds = position.get_trade_age_seconds()

        if trade_age_seconds < config.cooldown_seconds:
            logger.debug(
                f"Position {position.ticket} cooldown active: "
                f"{trade_age_seconds}s < {config.cooldown_seconds}s"
            )
            return True

        return False

    async def check_breakeven_trigger(
        self, position: TradePosition, config: BreakevenConfig
    ) -> Optional[BreakevenUpdate]:
        """
        Check and trigger breakeven for a position if conditions are met.

        Breakeven logic:
        - Check if position is already locked at breakeven (skip if so)
        - Check if cooldown period has passed
        - Check if position has reached profit_trigger_r profit (default 1.5R)
        - Calculate breakeven price (entry + buffer)
        - Update SL to breakeven price
        - Lock position at breakeven (never move back)

        Args:
            position: TradePosition to check
            config: BreakevenConfig with parameters

        Returns:
            BreakevenUpdate if SL was updated, None otherwise
        """
        if not config.enabled:
            logger.debug(f"Breakeven disabled for position {position.ticket}")
            return None

        # Check if position has a stop loss
        if position.stop_loss is None:
            logger.debug(f"Position {position.ticket} has no stop loss, skipping")
            return None

        # Check if already locked at breakeven
        if self._is_breakeven_locked(position):
            logger.debug(f"Position {position.ticket} already locked at breakeven")
            return None

        # Check cooldown period
        if self._is_cooldown_active(position, config):
            return None

        # Calculate initial risk and current profit in R
        initial_risk = self._calculate_initial_risk(position)

        if initial_risk == 0:
            logger.debug(f"Position {position.ticket} has zero initial risk, skipping")
            return None

        # Calculate current profit in R multiples
        # Use small tolerance to handle floating point precision issues
        tolerance = 1e-9
        current_profit_r = position.profit / initial_risk

        # Check if profit trigger is met
        if current_profit_r < config.profit_trigger_r - tolerance:
            logger.debug(
                f"Position {position.ticket} not at breakeven trigger yet: "
                f"{current_profit_r:.2f}R < {config.profit_trigger_r}R"
            )
            return None

        # Calculate breakeven price
        breakeven_price = self.calculate_breakeven_price(position, config)

        # Verify breakeven is better than current SL
        current_sl = position.stop_loss

        if not self._is_breakeven_improvement(position, breakeven_price):
            logger.debug(
                f"Breakeven price {breakeven_price:.5f} would not improve "
                f"current SL {current_sl:.5f}, skipping update"
            )
            return None

        # Send update to MT5
        if self._mt5 is not None:
            await self._send_sl_update_to_mt5(position, breakeven_price)
        else:
            logger.debug(
                f"MT5 connector not configured, would update SL to {breakeven_price:.5f}"
            )

        # Create update record
        update = BreakevenUpdate(
            ticket=position.ticket,
            old_stop_loss=current_sl,
            new_stop_loss=breakeven_price,
            current_price=position.current_price,
            profit_r=current_profit_r,
            reason=self._get_update_reason(position, breakeven_price, current_profit_r),
            timestamp=position.get_trade_age_seconds(),
        )

        # Log the update
        logger.info(
            f"Breakeven triggered for position {position.ticket} ({position.symbol} {position.direction}): "
            f"SL {current_sl:.5f} -> {breakeven_price:.5f} "
            f"| Price: {position.current_price:.5f} "
            f"| Profit: {current_profit_r:.2f}R "
            f"| Entry: {position.entry_price:.5f}"
        )

        # Update position stop loss
        position.stop_loss = breakeven_price

        # Lock position at breakeven
        self._breakeven_locked.add(position.ticket)

        # Store update in history
        self._update_history.append(update)

        # Send alert if alert system is configured
        if self._alert_system is not None:
            try:
                import asyncio
                asyncio.create_task(
                    self._alert_system.alert_breakeven_triggered(
                        ticket=position.ticket,
                        symbol=position.symbol,
                        stop_loss=breakeven_price,
                        entry_price=position.entry_price,
                        profit_r=current_profit_r,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send breakeven alert: {e}")

        return update

    def _is_breakeven_improvement(
        self, position: TradePosition, breakeven_price: float
    ) -> bool:
        """
        Check if breakeven price is an improvement over current stop loss.

        For LONG: breakeven must be higher than current SL
        For SHORT: breakeven must be lower than current SL

        Args:
            position: TradePosition
            breakeven_price: Proposed breakeven price

        Returns:
            True if breakeven is an improvement
        """
        if position.stop_loss is None:
            return True

        if position.direction == "BUY":
            # For LONG, breakeven should be above current SL (or closer to entry)
            return breakeven_price > position.stop_loss
        else:
            # For SHORT, breakeven should be below current SL
            return breakeven_price < position.stop_loss

    def _get_update_reason(
        self, position: TradePosition, breakeven_price: float, profit_r: float
    ) -> str:
        """
        Get a human-readable reason for the breakeven update.

        Args:
            position: TradePosition
            breakeven_price: New breakeven price
            profit_r: Current profit in R multiples

        Returns:
            Reason string
        """
        return (
            f"Profit target reached ({profit_r:.2f}R >= {BreakevenConfig().profit_trigger_r}R), "
            f"SL moved to breakeven to prevent loss"
        )

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

    def get_update_history(self, ticket: Optional[int] = None) -> list[BreakevenUpdate]:
        """
        Get breakeven update history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of BreakevenUpdate records
        """
        if ticket is None:
            return self._update_history.copy()
        return [u for u in self._update_history if u.ticket == ticket]

    def clear_update_history(self) -> None:
        """Clear the breakeven update history."""
        self._update_history.clear()
        logger.debug("Breakeven update history cleared")

    def is_position_locked(self, ticket: int) -> bool:
        """
        Check if a position is locked at breakeven.

        Args:
            ticket: Position ticket number

        Returns:
            True if position is locked at breakeven
        """
        return ticket in self._breakeven_locked

    def unlock_position(self, ticket: int) -> None:
        """
        Unlock a position from breakeven (use with caution).

        This allows the position's SL to be moved again.
        This should only be used in special circumstances.

        Args:
            ticket: Position ticket number
        """
        if ticket in self._breakeven_locked:
            self._breakeven_locked.remove(ticket)
            logger.warning(f"Position {ticket} unlocked from breakeven")

    def get_locked_positions(self) -> set[int]:
        """
        Get all positions currently locked at breakeven.

        Returns:
            Set of ticket numbers
        """
        return self._breakeven_locked.copy()
