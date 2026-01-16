"""
Partial Profit Manager for active trade management.

This module implements the partial profit taking mechanism that closes
portions of positions at predefined profit levels to bank profits early.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .trade_state import TradePosition, TradeState


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PartialProfitConfig:
    """
    Configuration for partial profit taking behavior.

    Attributes:
        close_50_at_r: Close 50% at this R multiple (default: 2.0)
        close_25_at_r: Close 25% at this R multiple (default: 3.0)
        close_remaining_at_r: Close remaining at this R multiple (default: 5.0)
        cooldown_seconds: Cooldown between partial closes (default: 60)
        move_to_breakeven_after_first: Move SL to breakeven after first partial (default: True)
        enabled: Whether partial profit taking is enabled (default: True)
    """

    close_50_at_r: float = 2.0
    close_25_at_r: float = 3.0
    close_remaining_at_r: float = 5.0
    cooldown_seconds: int = 60  # 1 minute
    move_to_breakeven_after_first: bool = True
    enabled: bool = True


@dataclass
class PartialProfitLevel:
    """
    Defines a partial profit close level.

    Attributes:
        r_multiple: R multiple trigger level
        close_percentage: Percentage of position to close (0.0 to 1.0)
        description: Human-readable description
    """

    r_multiple: float
    close_percentage: float
    description: str


@dataclass
class PartialProfitUpdate:
    """
    Record of a partial profit close.

    Attributes:
        ticket: Position ticket number
        original_volume: Original position volume when first opened
        closed_lots: Number of lots closed
        remaining_lots: Number of lots remaining
        close_price: Price at which position was closed
        profit_at_close: Profit in currency units
        profit_r_multiple: Current profit in R multiples
        close_percentage: Percentage of ORIGINAL position closed (0.0 to 1.0)
        reason: Reason for the close
        timestamp: When the close occurred
    """

    ticket: int
    original_volume: float
    closed_lots: float
    remaining_lots: float
    close_price: float
    profit_at_close: float
    profit_r_multiple: float
    close_percentage: float
    reason: str
    timestamp: float


class PartialProfitManager:
    """
    Manages partial profit taking for open positions.

    Features:
    - Closes 50% at 2R profit (configurable)
    - Closes 25% at 3R profit (configurable)
    - Closes remaining at 5R profit or trailing stop (configurable)
    - Moves SL to breakeven after first partial close
    - Tracks partial closes in database
    - Comprehensive logging of all operations

    Usage:
        manager = PartialProfitManager(mt5_connector)
        config = PartialProfitConfig(close_50_at_r=2.0)

        # Check and execute partial profit close for a position
        update = await manager.check_partial_close_triggers(position, config)
        if update:
            logger.info(f"Partial profit taken: {update.close_percentage*100}%")
    """

    def __init__(
        self,
        mt5_connector: Optional["MT5Connector"] = None,
        alert_system: Optional["ManagementAlertSystem"] = None,
    ):
        """
        Initialize the PartialProfitManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
            alert_system: ManagementAlertSystem instance for sending alerts
        """
        self._mt5 = mt5_connector
        self._alert_system = alert_system
        self._close_history: list[PartialProfitUpdate] = []
        self._last_close_time: dict[int, float] = {}  # ticket -> timestamp
        self._original_volumes: dict[int, float] = {}  # ticket -> original volume

        logger.info("PartialProfitManager initialized")

    def _get_original_volume(self, position: TradePosition) -> float:
        """
        Get the original volume for a position.

        Args:
            position: TradePosition

        Returns:
            Original volume (stored on first close)
        """
        if position.ticket not in self._original_volumes:
            # First time seeing this position, store current volume as original
            self._original_volumes[position.ticket] = position.volume

        return self._original_volumes[position.ticket]

    def get_partial_close_levels(self, config: PartialProfitConfig) -> list[PartialProfitLevel]:
        """
        Get the configured partial close levels.

        Args:
            config: PartialProfitConfig with parameters

        Returns:
            List of PartialProfitLevel in ascending order
        """
        return [
            PartialProfitLevel(
                r_multiple=config.close_50_at_r,
                close_percentage=0.50,
                description=f"Close 50% at {config.close_50_at_r}R"
            ),
            PartialProfitLevel(
                r_multiple=config.close_25_at_r,
                close_percentage=0.25,
                description=f"Close 25% at {config.close_25_at_r}R"
            ),
            PartialProfitLevel(
                r_multiple=config.close_remaining_at_r,
                close_percentage=1.0,  # Close remaining
                description=f"Close remaining at {config.close_remaining_at_r}R"
            ),
        ]

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

    def _calculate_r_multiple(self, position: TradePosition) -> float:
        """
        Calculate current profit in R multiples.

        Args:
            position: TradePosition

        Returns:
            Current profit in R multiples
        """
        initial_risk = self._calculate_initial_risk(position)

        if initial_risk == 0:
            return 0.0

        return position.profit / initial_risk

    def _get_remaining_percentage(self, position: TradePosition) -> float:
        """
        Calculate remaining position percentage based on close history.

        Args:
            position: TradePosition

        Returns:
            Remaining percentage (0.0 to 1.0)
        """
        # Get all closes for this position
        closes = [c for c in self._close_history if c.ticket == position.ticket]

        if not closes:
            return 1.0  # Full position remaining

        # Sum up closed percentages
        total_closed = sum(c.close_percentage for c in closes)

        # Ensure we don't go below 0
        remaining = max(0.0, 1.0 - total_closed)

        return remaining

    def _is_cooldown_active(self, position: TradePosition, config: PartialProfitConfig) -> bool:
        """
        Check if partial close cooldown is still active.

        Args:
            position: TradePosition to check
            config: PartialProfitConfig with cooldown parameters

        Returns:
            True if cooldown is still active
        """
        if position.ticket not in self._last_close_time:
            return False

        current_time = position.get_trade_age_seconds()
        last_close = self._last_close_time[position.ticket]
        time_since_close = current_time - last_close

        if time_since_close < config.cooldown_seconds:
            logger.debug(
                f"Position {position.ticket} cooldown active: "
                f"{time_since_close}s < {config.cooldown_seconds}s"
            )
            return True

        return False

    def _determine_close_amount(
        self, position: TradePosition, level: PartialProfitLevel
    ) -> float:
        """
        Determine how much to close based on level and remaining position.

        Args:
            position: TradePosition
            level: PartialProfitLevel triggering close

        Returns:
            Percentage of original position to close (0.0 to 1.0)
        """
        remaining = self._get_remaining_percentage(position)

        # Calculate actual close percentage based on remaining
        if level.close_percentage >= 1.0:
            # Close remaining
            return remaining
        else:
            # Close specified percentage, but not more than remaining
            return min(level.close_percentage, remaining)

    async def check_partial_close_triggers(
        self, position: TradePosition, config: PartialProfitConfig
    ) -> Optional[PartialProfitUpdate]:
        """
        Check and execute partial profit closes for a position.

        Partial profit logic:
        - Check if partial profit is enabled
        - Calculate current profit in R multiples
        - Check against configured levels (2R, 3R, 5R)
        - Execute partial close via MT5 if trigger hit
        - Move SL to breakeven after first partial close
        - Track partial closes in database

        Args:
            position: TradePosition to check
            config: PartialProfitConfig with parameters

        Returns:
            PartialProfitUpdate if position was closed, None otherwise
        """
        if not config.enabled:
            logger.debug(f"Partial profit disabled for position {position.ticket}")
            return None

        # Check if cooldown is active
        if self._is_cooldown_active(position, config):
            return None

        # Calculate current profit in R multiples
        current_r = self._calculate_r_multiple(position)

        if current_r <= 0:
            logger.debug(f"Position {position.ticket} not profitable, skipping")
            return None

        # Get configured levels
        levels = self.get_partial_close_levels(config)

        # Check each level to see if triggered
        for level in levels:
            # Check if profit level is reached
            if current_r < level.r_multiple:
                logger.debug(
                    f"Position {position.ticket} not at {level.description} yet: "
                    f"{current_r:.2f}R < {level.r_multiple}R"
                )
                continue

            # Determine how much to close
            close_percentage = self._determine_close_amount(position, level)

            if close_percentage <= 0:
                logger.debug(f"Position {position.ticket} nothing left to close")
                continue

            # Execute the partial close
            return await self._execute_partial_close(
                position, level, close_percentage, current_r, config
            )

        logger.debug(f"Position {position.ticket} no partial close triggers met")
        return None

    async def _execute_partial_close(
        self,
        position: TradePosition,
        level: PartialProfitLevel,
        close_percentage: float,
        current_r: float,
        config: PartialProfitConfig,
    ) -> Optional[PartialProfitUpdate]:
        """
        Execute a partial close for a position.

        Args:
            position: TradePosition to close
            level: PartialProfitLevel that triggered
            close_percentage: Percentage of ORIGINAL position to close (0.0 to 1.0)
            current_r: Current profit in R multiples
            config: PartialProfitConfig

        Returns:
            PartialProfitUpdate if successful, None otherwise
        """
        # Get original volume for calculations
        original_volume = self._get_original_volume(position)

        # Calculate lots to close based on ORIGINAL volume
        lots_to_close = original_volume * close_percentage
        lots_remaining = position.volume - lots_to_close

        # Validate we're not closing more than we have
        if lots_to_close > position.volume:
            logger.error(
                f"Attempting to close {lots_to_close} lots but only have {position.volume}"
            )
            return None

        # Send close order to MT5
        if self._mt5 is not None:
            close_price = await self._send_partial_close_to_mt5(
                position, lots_to_close
            )
            if close_price is None:
                logger.error(f"Failed to close partial position {position.ticket}")
                return None
        else:
            logger.debug(
                f"MT5 connector not configured, would close {lots_to_close} lots"
            )
            close_price = position.current_price

        # Calculate profit at close (proportional to position closed)
        profit_at_close = position.profit * (lots_to_close / position.volume)

        # Create update record
        update = PartialProfitUpdate(
            ticket=position.ticket,
            original_volume=original_volume,
            closed_lots=lots_to_close,
            remaining_lots=lots_remaining,
            close_price=close_price,
            profit_at_close=profit_at_close,
            profit_r_multiple=current_r,
            close_percentage=close_percentage,
            reason=level.description,
            timestamp=position.get_trade_age_seconds(),
        )

        # Log the close
        logger.info(
            f"Partial profit closed for position {position.ticket} ({position.symbol} {position.direction}): "
            f"{close_percentage*100:.1f}% ({lots_to_close:.2f} lots) "
            f"| Price: {close_price:.5f} "
            f"| Profit: {profit_at_close:.2f} ({current_r:.2f}R) "
            f"| Remaining: {lots_remaining:.2f} lots"
        )

        # Update last close time for cooldown
        self._last_close_time[position.ticket] = update.timestamp

        # Store update in history
        self._close_history.append(update)

        # Send alert if alert system is configured
        if self._alert_system is not None:
            try:
                import asyncio
                asyncio.create_task(
                    self._alert_system.alert_partial_profit_taken(
                        ticket=position.ticket,
                        symbol=position.symbol,
                        percentage_closed=update.close_percentage * 100,
                        profit_banked=update.profit_at_close,
                        remaining_volume=update.remaining_lots,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send partial profit alert: {e}")

        # Move SL to breakeven after first partial close if configured
        if config.move_to_breakeven_after_first and self._get_remaining_percentage(position) <= 0.5:
            await self._move_to_breakeven(position)

        # Update position state
        if position.state == TradeState.OPEN:
            position.transition_state(
                TradeState.PARTIAL,
                reason=f"First partial close at {current_r:.2f}R"
            )

        # Update position volume
        position.volume = lots_remaining

        return update

    async def _send_partial_close_to_mt5(
        self, position: TradePosition, lots: float
    ) -> Optional[float]:
        """
        Send partial close order to MT5.

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
                f"MT5 connector not configured, skipping partial close for position {position.ticket}"
            )
            return None

        try:
            # Call the MT5 API to close partial position
            # Note: Using the actual position's current_price as close price
            # since MT5 will execute at market price
            close_price = await self._mt5.close_position(
                ticket=position.ticket,
                lots=lots,
            )
            logger.debug(
                f"MT5 partial close sent for position {position.ticket}: "
                f"{lots} lots at {close_price:.5f}"
            )
            return close_price
        except Exception as e:
            logger.error(f"Failed to send partial close to MT5: {e}")
            raise ConnectionError(f"MT5 partial close failed: {e}") from e

    async def _move_to_breakeven(self, position: TradePosition) -> None:
        """
        Move stop loss to breakeven after partial close.

        Args:
            position: TradePosition to update

        Note:
            This is a simple breakeven implementation.
            In production, this would use the BreakevenManager.
        """
        if position.stop_loss is None:
            return

        # For simplicity, move SL to entry price
        # In production, use BreakevenManager with proper buffer
        new_sl = position.entry_price

        if self._mt5 is not None:
            try:
                await self._mt5.update_stop_loss(position.ticket, new_sl)
                logger.info(
                    f"Moved SL to breakeven for position {position.ticket}: "
                    f"{position.stop_loss:.5f} -> {new_sl:.5f}"
                )
                position.stop_loss = new_sl
            except Exception as e:
                logger.error(f"Failed to move SL to breakeven: {e}")
        else:
            logger.debug(
                f"MT5 connector not configured, would move SL to breakeven {new_sl:.5f}"
            )

    def get_close_history(self, ticket: Optional[int] = None) -> list[PartialProfitUpdate]:
        """
        Get partial profit close history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of PartialProfitUpdate records
        """
        if ticket is None:
            return self._close_history.copy()
        return [c for c in self._close_history if c.ticket == ticket]

    def clear_close_history(self) -> None:
        """Clear the partial profit close history."""
        self._close_history.clear()
        self._last_close_time.clear()
        self._original_volumes.clear()
        logger.debug("Partial profit close history cleared")

    def get_total_closed_percentage(self, ticket: int) -> float:
        """
        Get total percentage closed for a position.

        Args:
            ticket: Position ticket number

        Returns:
            Total percentage closed (0.0 to 1.0)
        """
        closes = self.get_close_history(ticket)
        return sum(c.close_percentage for c in closes)
