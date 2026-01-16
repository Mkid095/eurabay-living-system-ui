"""
Active Trade Manager - Foundation class for monitoring and managing open positions.

This module provides the core trade manager that monitors all open positions,
calculates PnL, tracks trade age, and manages trade states.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass

from .trade_state import TradePosition, TradeState, TradeStateMachine


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MT5Position:
    """Raw MT5 position data structure."""

    ticket: int
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    volume: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    profit: float
    swap: float
    commission: float
    entry_time: datetime


class ActiveTradeManager:
    """
    Foundation trade manager that monitors and manages all open positions.

    Features:
    - Monitors open trades every 5 seconds
    - Fetches positions from MT5
    - Calculates current PnL for each position
    - Tracks trade age (time since entry)
    - Manages trade state (pending, open, partial, closed)
    - Comprehensive logging for all operations
    """

    # Monitoring loop interval in seconds
    MONITORING_INTERVAL: float = 5.0

    def __init__(self, mt5_connector: Optional["MT5Connector"] = None):
        """
        Initialize the ActiveTradeManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
        """
        self._mt5 = mt5_connector
        self._positions: dict[int, TradePosition] = {}
        self._is_monitoring: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._on_position_update: Optional[Callable[[TradePosition], None]] = None

        logger.info("ActiveTradeManager initialized")

    def set_position_update_callback(
        self, callback: Callable[[TradePosition], None]
    ) -> None:
        """
        Set callback for position updates.

        Args:
            callback: Function to call when a position is updated
        """
        self._on_position_update = callback
        logger.debug("Position update callback registered")

    async def fetch_open_positions(self) -> list[MT5Position]:
        """
        Fetch all open positions from MT5.

        Returns:
            List of MT5Position objects representing open positions

        Raises:
            ConnectionError: If MT5 is not connected
        """
        if self._mt5 is None:
            logger.warning("MT5 connector not configured, returning empty list")
            return []

        try:
            raw_positions = await self._mt5.get_positions()
            logger.info(f"Fetched {len(raw_positions)} open positions from MT5")
            return raw_positions
        except Exception as e:
            logger.error(f"Failed to fetch positions from MT5: {e}")
            raise ConnectionError(f"MT5 connection failed: {e}") from e

    def calculate_current_pnl(self, position: TradePosition) -> float:
        """
        Calculate the current PnL for a position.

        Args:
            position: TradePosition to calculate PnL for

        Returns:
            Current PnL value (profit/loss + swap + commission)
        """
        # Current PnL = unrealized profit/loss + swap + commission
        pnl = position.profit + position.swap + position.commission

        logger.debug(
            f"Position {position.ticket} PnL: {pnl:.2f} "
            f"(profit: {position.profit:.2f}, swap: {position.swap:.2f}, "
            f"commission: {position.commission:.2f})"
        )

        return pnl

    def get_trade_age(self, position: TradePosition) -> timedelta:
        """
        Get the age of a trade (time since entry).

        Args:
            position: TradePosition to get age for

        Returns:
            timedelta representing time since entry
        """
        age = timedelta(seconds=position.get_trade_age_seconds())

        logger.debug(f"Position {position.ticket} age: {age}")

        return age

    def get_trade_state(self, position: TradePosition) -> TradeState:
        """
        Get the current state of a trade.

        Args:
            position: TradePosition to get state for

        Returns:
            Current TradeState of the position
        """
        state = TradeStateMachine.get_state(position)

        logger.debug(f"Position {position.ticket} state: {state.value}")

        return state

    def _convert_mt5_to_trade_position(self, mt5_pos: MT5Position) -> TradePosition:
        """
        Convert MT5 position to TradePosition.

        Args:
            mt5_pos: MT5Position from MT5 API

        Returns:
            TradePosition object
        """
        # Determine initial state based on whether position has partial closes
        # For now, all fetched positions are OPEN
        initial_state = TradeState.OPEN

        position = TradePosition(
            ticket=mt5_pos.ticket,
            symbol=mt5_pos.symbol,
            direction=mt5_pos.direction,
            entry_price=mt5_pos.entry_price,
            current_price=mt5_pos.entry_price,  # Will be updated
            volume=mt5_pos.volume,
            stop_loss=mt5_pos.stop_loss,
            take_profit=mt5_pos.take_profit,
            entry_time=mt5_pos.entry_time,
            profit=mt5_pos.profit,
            swap=mt5_pos.swap,
            commission=mt5_pos.commission,
            state=initial_state,
        )

        logger.debug(
            f"Converted MT5 position {mt5_pos.ticket} to TradePosition: {mt5_pos.symbol} {mt5_pos.direction}"
        )

        return position

    async def _update_position_prices(self) -> None:
        """
        Update current prices for all tracked positions.

        Fetches latest market data and updates current_price for each position.
        """
        if self._mt5 is None:
            return

        for ticket, position in self._positions.items():
            try:
                current_price = await self._mt5.get_current_price(position.symbol)
                position.current_price = current_price
                logger.debug(
                    f"Updated price for {position.symbol}: {current_price:.5f}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to update price for {position.symbol}: {e}"
                )

    async def monitor_open_trades(self) -> None:
        """
        Main monitoring loop that runs every 5 seconds.

        This is the core method that:
        1. Fetches all open positions from MT5
        2. Updates current prices for all positions
        3. Calculates PnL for each position
        4. Checks trade age
        5. Updates trade state
        6. Calls position update callbacks

        This runs continuously until stop_monitoring() is called.
        """
        logger.info("Starting trade monitoring loop")
        self._is_monitoring = True

        while self._is_monitoring:
            try:
                # Fetch open positions from MT5
                mt5_positions = await self.fetch_open_positions()

                # Update current prices
                await self._update_position_prices()

                # Process each position
                for mt5_pos in mt5_positions:
                    # Check if we already track this position
                    if mt5_pos.ticket not in self._positions:
                        # New position - convert and add
                        position = self._convert_mt5_to_trade_position(mt5_pos)
                        self._positions[mt5_pos.ticket] = position
                        logger.info(
                            f"New position tracked: {position.symbol} {position.direction} "
                            f"@ {position.entry_price:.5f}"
                        )
                    else:
                        # Existing position - update data
                        position = self._positions[mt5_pos.ticket]
                        position.profit = mt5_pos.profit
                        position.swap = mt5_pos.swap
                        position.commission = mt5_pos.commission
                        position.volume = mt5_pos.volume
                        position.stop_loss = mt5_pos.stop_loss
                        position.take_profit = mt5_pos.take_profit

                    # Get position and calculate metrics
                    position = self._positions[mt5_pos.ticket]

                    # Calculate PnL
                    pnl = self.calculate_current_pnl(position)

                    # Get trade age
                    age = self.get_trade_age(position)

                    # Get trade state
                    state = self.get_trade_state(position)

                    # Log position summary
                    logger.info(
                        f"Position {position.ticket}: {position.symbol} {position.direction} | "
                        f"PnL: {pnl:.2f} | Age: {age} | State: {state.value} | "
                        f"Price: {position.current_price:.5f}"
                    )

                    # Trigger callback if registered
                    if self._on_position_update:
                        try:
                            self._on_position_update(position)
                        except Exception as e:
                            logger.error(
                                f"Error in position update callback: {e}",
                                exc_info=True,
                            )

                # Remove closed positions
                current_tickets = {pos.ticket for pos in mt5_positions}
                closed_tickets = set(self._positions.keys()) - current_tickets

                for ticket in closed_tickets:
                    closed_position = self._positions.pop(ticket)
                    closed_position.transition_state(
                        TradeState.CLOSED, "Position closed in MT5"
                    )
                    logger.info(
                        f"Position {ticket} closed, removed from tracking"
                    )

                # Wait for next iteration
                await asyncio.sleep(self.MONITORING_INTERVAL)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Continue monitoring despite errors
                await asyncio.sleep(self.MONITORING_INTERVAL)

    async def start_monitoring(self) -> None:
        """
        Start the monitoring loop in the background.

        Creates an async task that runs the monitor_open_trades() loop.
        """
        if self._is_monitoring:
            logger.warning("Monitoring already active, ignoring start request")
            return

        logger.info("Starting background monitoring task")
        self._monitor_task = asyncio.create_task(self.monitor_open_trades())

    async def stop_monitoring(self) -> None:
        """
        Stop the monitoring loop.

        Signals the monitor_open_trades() loop to stop and waits for completion.
        """
        if not self._is_monitoring:
            logger.warning("Monitoring not active, ignoring stop request")
            return

        logger.info("Stopping monitoring loop")
        self._is_monitoring = False

        if self._monitor_task:
            await asyncio.wait_for(self._monitor_task, timeout=10.0)
            self._monitor_task = None

        logger.info("Monitoring loop stopped")

    def get_tracked_positions(self) -> dict[int, TradePosition]:
        """
        Get all currently tracked positions.

        Returns:
            Dictionary mapping ticket numbers to TradePosition objects
        """
        return self._positions.copy()

    def get_position(self, ticket: int) -> Optional[TradePosition]:
        """
        Get a specific tracked position by ticket number.

        Args:
            ticket: Position ticket number

        Returns:
            TradePosition if found, None otherwise
        """
        return self._positions.get(ticket)

    def is_monitoring(self) -> bool:
        """
        Check if the monitoring loop is currently running.

        Returns:
            True if monitoring is active, False otherwise
        """
        return self._is_monitoring


# Mock MT5 connector for testing
class MT5Connector:
    """
    Mock MT5 connector for testing and development.

    In production, this would interface with the actual MetaTrader5 API.
    """

    async def get_positions(self) -> list[MT5Position]:
        """Get all open positions from MT5."""
        # This would call the actual MT5 API in production
        return []

    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        # This would call the actual MT5 API in production
        return 0.0
