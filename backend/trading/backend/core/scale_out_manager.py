"""
Scale Out Manager for active trade management.

This module implements the scale-out mechanism that closes portions
of positions at predefined profit levels to lock in profits while
keeping upside potential on remaining position.
"""

import logging
import time
from typing import Optional
from dataclasses import dataclass

from .trade_state import TradePosition, TradeState


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ScaleOutConfig:
    """
    Configuration for scale-out behavior.

    Attributes:
        close_25_at_2r: Close 25% at 2R profit (default: True)
        close_25_at_3r: Close 25% at 3R profit (default: True)
        close_25_at_4r: Close 25% at 4R profit (default: True)
        hold_rest: Hold remaining position instead of closing (default: True)
        alternative_50_50: Use alternative 50% at 2R, 50% at 4R strategy (default: False)
        cooldown_seconds: Cooldown between scale-outs (default: 60)
        move_to_breakeven_after_first: Move SL to breakeven after first scale-out (default: True)
        enabled: Whether scale-out is enabled (default: True)
    """

    close_25_at_2r: bool = True
    close_25_at_3r: bool = True
    close_25_at_4r: bool = True
    hold_rest: bool = True
    alternative_50_50: bool = False
    cooldown_seconds: int = 60  # 1 minute
    move_to_breakeven_after_first: bool = True
    enabled: bool = True


@dataclass
class ScaleOutLevel:
    """
    Defines a scale-out close level.

    Attributes:
        r_multiple: R multiple trigger level
        close_percentage: Percentage of position to close (0.0 to 1.0)
        description: Human-readable description
    """

    r_multiple: float
    close_percentage: float
    description: str


@dataclass
class ScaleOutUpdate:
    """
    Record of a scale-out operation.

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


class ScaleOutManager:
    """
    Manages scale-out operations for open positions.

    Features:
    - Close 25% at 2R, 25% at 3R, 25% at 4R, hold rest (configurable)
    - Alternative strategy: close 50% at 2R, 50% at 4R
    - Move SL to breakeven after first scale-out
    - Track scale-out operations in database
    - Comprehensive logging of all operations

    Usage:
        manager = ScaleOutManager(mt5_connector)
        config = ScaleOutConfig(close_25_at_2r=True)

        # Check and execute scale-out for a position
        update = await manager.check_scale_out_trigger(position, config)
        if update:
            logger.info(f"Scale-out executed: {update.close_percentage*100}%")
    """

    def __init__(self, mt5_connector: Optional["MT5Connector"] = None):
        """
        Initialize the ScaleOutManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
        """
        self._mt5 = mt5_connector
        self._scale_out_history: list[ScaleOutUpdate] = []
        self._last_scale_out_time: dict[int, float] = {}  # ticket -> timestamp
        self._original_volumes: dict[int, float] = {}  # ticket -> original volume

        logger.info("ScaleOutManager initialized")

    def _get_original_volume(self, position: TradePosition) -> float:
        """
        Get the original volume for a position.

        Args:
            position: TradePosition

        Returns:
            Original volume (stored on first scale-out)
        """
        if position.ticket not in self._original_volumes:
            # First time seeing this position, store current volume as original
            self._original_volumes[position.ticket] = position.volume

        return self._original_volumes[position.ticket]

    def get_scale_out_levels(self, config: ScaleOutConfig) -> list[ScaleOutLevel]:
        """
        Get the configured scale-out levels.

        Args:
            config: ScaleOutConfig with parameters

        Returns:
            List of ScaleOutLevel in ascending order
        """
        if config.alternative_50_50:
            return [
                ScaleOutLevel(
                    r_multiple=2.0,
                    close_percentage=0.50,
                    description="Close 50% at 2R (alt strategy)"
                ),
                ScaleOutLevel(
                    r_multiple=4.0,
                    close_percentage=0.50,
                    description="Close 50% at 4R (alt strategy)"
                ),
            ]
        else:
            levels = []
            if config.close_25_at_2r:
                levels.append(
                    ScaleOutLevel(
                        r_multiple=2.0,
                        close_percentage=0.25,
                        description="Close 25% at 2R"
                    )
                )
            if config.close_25_at_3r:
                levels.append(
                    ScaleOutLevel(
                        r_multiple=3.0,
                        close_percentage=0.25,
                        description="Close 25% at 3R"
                    )
                )
            if config.close_25_at_4r:
                levels.append(
                    ScaleOutLevel(
                        r_multiple=4.0,
                        close_percentage=0.25,
                        description="Close 25% at 4R"
                    )
                )
            return levels

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
        Calculate remaining position percentage based on scale-out history.

        Args:
            position: TradePosition

        Returns:
            Remaining percentage (0.0 to 1.0)
        """
        # Get all scale-outs for this position
        scale_outs = [s for s in self._scale_out_history if s.ticket == position.ticket]

        if not scale_outs:
            return 1.0  # Full position remaining

        # Sum up closed percentages
        total_closed = sum(s.close_percentage for s in scale_outs)

        # Ensure we don't go below 0
        remaining = max(0.0, 1.0 - total_closed)

        return remaining

    def _is_cooldown_active(self, position: TradePosition, config: ScaleOutConfig) -> bool:
        """
        Check if scale-out cooldown is still active.

        Args:
            position: TradePosition to check
            config: ScaleOutConfig with cooldown parameters

        Returns:
            True if cooldown is still active
        """
        if position.ticket not in self._last_scale_out_time:
            return False

        current_time = time.time()
        last_scale_out = self._last_scale_out_time[position.ticket]
        time_since_scale_out = current_time - last_scale_out

        if time_since_scale_out < config.cooldown_seconds:
            logger.debug(
                f"Position {position.ticket} cooldown active: "
                f"{time_since_scale_out:.1f}s < {config.cooldown_seconds}s"
            )
            return True

        return False

    def _determine_close_amount(
        self, position: TradePosition, level: ScaleOutLevel, config: ScaleOutConfig
    ) -> float:
        """
        Determine how much to close based on level and remaining position.

        Args:
            position: TradePosition
            level: ScaleOutLevel triggering close
            config: ScaleOutConfig

        Returns:
            Percentage of original position to close (0.0 to 1.0)
        """
        remaining = self._get_remaining_percentage(position)

        # Calculate actual close percentage based on remaining
        if config.hold_rest and level.close_percentage >= remaining:
            # Hold rest strategy - don't close last portion
            return remaining * 0.5  # Close half of remaining
        else:
            # Close specified percentage, but not more than remaining
            return min(level.close_percentage, remaining)

    async def check_scale_out_trigger(
        self, position: TradePosition, config: ScaleOutConfig
    ) -> Optional[ScaleOutUpdate]:
        """
        Check and execute scale-out for a position.

        Scale-out logic:
        - Check if scale-out is enabled
        - Calculate current profit in R multiples
        - Check against configured levels (2R, 3R, 4R or alt 2R, 4R)
        - Execute scale-out via MT5 if trigger hit
        - Move SL to breakeven after first scale-out
        - Track scale-out operations in database

        Args:
            position: TradePosition to check
            config: ScaleOutConfig with parameters

        Returns:
            ScaleOutUpdate if position was scaled out, None otherwise
        """
        if not config.enabled:
            logger.debug(f"Scale-out disabled for position {position.ticket}")
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
        levels = self.get_scale_out_levels(config)

        # Check each level to see if triggered
        for level in levels:
            # Check if profit level is reached (with small tolerance for floating point precision)
            if current_r < level.r_multiple - 0.01:  # 0.01 tolerance for floating point precision
                logger.debug(
                    f"Position {position.ticket} not at {level.description} yet: "
                    f"{current_r:.2f}R < {level.r_multiple}R"
                )
                continue

            # Determine how much to close
            close_percentage = self._determine_close_amount(position, level, config)

            if close_percentage <= 0:
                logger.debug(f"Position {position.ticket} nothing left to close")
                continue

            # Execute the scale-out
            return await self._execute_scale_out(
                position, level, close_percentage, current_r, config
            )

        logger.debug(f"Position {position.ticket} no scale-out triggers met")
        return None

    async def _execute_scale_out(
        self,
        position: TradePosition,
        level: ScaleOutLevel,
        close_percentage: float,
        current_r: float,
        config: ScaleOutConfig,
    ) -> Optional[ScaleOutUpdate]:
        """
        Execute a scale-out for a position.

        Args:
            position: TradePosition to scale out
            level: ScaleOutLevel that triggered
            close_percentage: Percentage of ORIGINAL position to close (0.0 to 1.0)
            current_r: Current profit in R multiples
            config: ScaleOutConfig

        Returns:
            ScaleOutUpdate if successful, None otherwise
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
            close_price = await self._send_scale_out_to_mt5(
                position, lots_to_close
            )
            if close_price is None:
                logger.error(f"Failed to scale-out position {position.ticket}")
                return None
        else:
            logger.debug(
                f"MT5 connector not configured, would close {lots_to_close} lots"
            )
            close_price = position.current_price

        # Calculate profit at close (proportional to position closed)
        profit_at_close = position.profit * (lots_to_close / position.volume)

        # Create update record
        update = ScaleOutUpdate(
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

        # Log the scale-out
        logger.info(
            f"Scale-out closed for position {position.ticket} ({position.symbol} {position.direction}): "
            f"{close_percentage*100:.1f}% ({lots_to_close:.2f} lots) "
            f"| Price: {close_price:.5f} "
            f"| Profit: {profit_at_close:.2f} ({current_r:.2f}R) "
            f"| Remaining: {lots_remaining:.2f} lots"
        )

        # Update last scale-out time for cooldown
        self._last_scale_out_time[position.ticket] = time.time()

        # Store update in history
        self._scale_out_history.append(update)

        # Move SL to breakeven after first scale-out if configured
        if config.move_to_breakeven_after_first and self._get_remaining_percentage(position) <= 0.75:
            await self._move_to_breakeven(position)

        # Update position state
        if position.state == TradeState.OPEN:
            position.transition_state(
                TradeState.SCALED_OUT,
                reason=f"First scale-out at {current_r:.2f}R"
            )
        elif position.state == TradeState.PARTIAL:
            position.transition_state(
                TradeState.SCALED_OUT,
                reason=f"Scale-out after partial profit at {current_r:.2f}R"
            )

        # Update position volume
        position.volume = lots_remaining

        return update

    async def _send_scale_out_to_mt5(
        self, position: TradePosition, lots: float
    ) -> Optional[float]:
        """
        Send scale-out order to MT5.

        Args:
            position: TradePosition to scale out
            lots: Number of lots to close

        Returns:
            Close price if successful, None otherwise

        Raises:
            ConnectionError: If MT5 close fails
        """
        if self._mt5 is None:
            logger.debug(
                f"MT5 connector not configured, skipping scale-out for position {position.ticket}"
            )
            return None

        try:
            # Call the MT5 API to close partial position
            close_price = await self._mt5.close_position(
                ticket=position.ticket,
                lots=lots,
            )
            logger.debug(
                f"MT5 scale-out sent for position {position.ticket}: "
                f"{lots} lots at {close_price:.5f}"
            )
            return close_price
        except Exception as e:
            logger.error(f"Failed to send scale-out to MT5: {e}")
            raise ConnectionError(f"MT5 scale-out failed: {e}") from e

    async def _move_to_breakeven(self, position: TradePosition) -> None:
        """
        Move stop loss to breakeven after scale-out.

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

    def get_scale_out_history(self, ticket: Optional[int] = None) -> list[ScaleOutUpdate]:
        """
        Get scale-out history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of ScaleOutUpdate records
        """
        if ticket is None:
            return self._scale_out_history.copy()
        return [s for s in self._scale_out_history if s.ticket == ticket]

    def clear_scale_out_history(self) -> None:
        """Clear the scale-out history."""
        self._scale_out_history.clear()
        self._last_scale_out_time.clear()
        self._original_volumes.clear()
        logger.debug("Scale-out history cleared")

    def get_total_scaled_out_percentage(self, ticket: int) -> float:
        """
        Get total percentage scaled out for a position.

        Args:
            ticket: Position ticket number

        Returns:
            Total percentage scaled out (0.0 to 1.0)
        """
        scale_outs = self.get_scale_out_history(ticket)
        return sum(s.close_percentage for s in scale_outs)
