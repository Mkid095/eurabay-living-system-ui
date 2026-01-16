"""
Manual Override Manager for active trade management.

This module provides manual control capabilities for traders to override
automated trade management when needed.
"""

import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .trade_state import TradePosition, TradeState


# Configure logging
logger = logging.getLogger(__name__)


class OverrideAction(Enum):
    """Types of manual override actions."""

    CLOSE_POSITION = "close_position"
    DISABLE_TRAILING_STOP = "disable_trailing_stop"
    DISABLE_BREAKEVEN = "disable_breakeven"
    SET_MANUAL_STOP_LOSS = "set_manual_stop_loss"
    SET_MANUAL_TAKE_PROFIT = "set_manual_take_profit"
    PAUSE_MANAGEMENT = "pause_management"
    RESUME_MANAGEMENT = "resume_management"


@dataclass
class OverrideRecord:
    """
    Record of a manual override action.

    Attributes:
        ticket: Position ticket number
        action: Type of override action
        previous_value: Value before override (if applicable)
        new_value: New value set by override (if applicable)
        timestamp: When the override was executed
        user: User who performed the override
        reason: Reason for the override
        confirmed: Whether the override required confirmation
    """

    ticket: int
    action: OverrideAction
    previous_value: Optional[float]
    new_value: Optional[float]
    timestamp: datetime
    user: str
    reason: str
    confirmed: bool

    def to_dict(self) -> dict:
        """Convert override record to dictionary for storage."""
        return {
            "ticket": self.ticket,
            "action": self.action.value,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "user": self.user,
            "reason": self.reason,
            "confirmed": self.confirmed,
        }


@dataclass
class OverrideState:
    """
    Current override state for a position.

    Attributes:
        trailing_stopped: Whether trailing stop is disabled
        breakeven_stopped: Whether breakeven is disabled
        management_paused: Whether active management is paused
        manual_stop_loss: Manual stop loss value (if set)
        manual_take_profit: Manual take profit value (if set)
    """

    trailing_stopped: bool = False
    breakeven_stopped: bool = False
    management_paused: bool = False
    manual_stop_loss: Optional[float] = None
    manual_take_profit: Optional[float] = None


@dataclass
class OverrideResult:
    """
    Result of a manual override operation.

    Attributes:
        success: Whether the override succeeded
        message: Human-readable result message
        action: The action that was performed
        position_state: Current position state after override
    """

    success: bool
    message: str
    action: OverrideAction
    position_state: str


class ManualOverrideManager:
    """
    Manages manual override capabilities for active trade management.

    Features:
    - Close position manually (full or partial)
    - Disable trailing stop for a position
    - Disable breakeven for a position
    - Set manual stop loss
    - Set manual take profit
    - Pause active management for a position
    - Resume active management for a position
    - Comprehensive logging of all override actions
    - Callback support for override notifications

    Usage:
        manager = ManualOverrideManager(mt5_connector)

        # Close a position
        result = await manager.close_position(
            position=trade_position,
            user="trader1",
            reason="Taking manual profit"
        )

        # Disable trailing stop
        result = await manager.disable_trailing_stop(
            position=trade_position,
            user="trader1",
            reason="Volatility too high"
        )

        # Set manual stop loss
        result = await manager.set_manual_stop_loss(
            position=trade_position,
            stop_loss=1.0850,
            user="trader1",
            reason="Support level"
        )
    """

    def __init__(
        self,
        mt5_connector: Optional["MT5Connector"] = None,
        alert_system: Optional["ManagementAlertSystem"] = None,
    ):
        """
        Initialize the ManualOverrideManager.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
            alert_system: ManagementAlertSystem instance for sending alerts
        """
        self._mt5 = mt5_connector
        self._alert_system = alert_system
        self._override_states: dict[int, OverrideState] = {}
        self._override_history: list[OverrideRecord] = []
        self._on_override_callback: Optional[Callable[[OverrideRecord], None]] = None

        logger.info("ManualOverrideManager initialized")

    def set_override_callback(
        self, callback: Callable[[OverrideRecord], None]
    ) -> None:
        """
        Set callback for manual override actions.

        Args:
            callback: Function to call when an override is executed
        """
        self._on_override_callback = callback
        logger.debug("Override callback registered")

    def get_override_state(self, ticket: int) -> OverrideState:
        """
        Get the current override state for a position.

        Args:
            ticket: Position ticket number

        Returns:
            OverrideState for the position (creates new if not exists)
        """
        if ticket not in self._override_states:
            self._override_states[ticket] = OverrideState()
        return self._override_states[ticket]

    async def close_position(
        self,
        position: TradePosition,
        user: str,
        reason: str,
        lots: Optional[float] = None,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Manually close a position (full or partial).

        Args:
            position: TradePosition to close
            user: User performing the override
            reason: Reason for closing the position
            lots: Optional number of lots to close (None = full position)
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome

        Raises:
            ValueError: If position is already closed
        """
        if position.state == TradeState.CLOSED:
            return OverrideResult(
                success=False,
                message=f"Position {position.ticket} is already closed",
                action=OverrideAction.CLOSE_POSITION,
                position_state=position.state.value,
            )

        logger.info(
            f"Manual close requested for position {position.ticket} "
            f"by user '{user}': {reason}"
        )

        try:
            # Execute close via MT5
            if self._mt5:
                if lots is None:
                    # Full close
                    await self._mt5.close_position(position.ticket)
                    closed_lots = position.volume
                else:
                    # Partial close
                    if lots > position.volume:
                        return OverrideResult(
                            success=False,
                            message=f"Cannot close {lots} lots, position only has {position.volume} lots",
                            action=OverrideAction.CLOSE_POSITION,
                            position_state=position.state.value,
                        )
                    await self._mt5.close_position(position.ticket, lots)
                    closed_lots = lots

                # Record the override
                record = OverrideRecord(
                    ticket=position.ticket,
                    action=OverrideAction.CLOSE_POSITION,
                    previous_value=position.volume,
                    new_value=position.volume - closed_lots,
                    timestamp=datetime.utcnow(),
                    user=user,
                    reason=reason,
                    confirmed=confirmed,
                )
                self._record_override(record, position.symbol)

                # Update position state
                if lots is None or closed_lots >= position.volume:
                    position.transition_state(TradeState.CLOSED, f"Manual close: {reason}")

                return OverrideResult(
                    success=True,
                    message=f"Closed {closed_lots} lots of position {position.ticket}",
                    action=OverrideAction.CLOSE_POSITION,
                    position_state=position.state.value,
                )
            else:
                # No MT5 connector - simulate for testing
                logger.warning("MT5 connector not configured, simulating close")
                record = OverrideRecord(
                    ticket=position.ticket,
                    action=OverrideAction.CLOSE_POSITION,
                    previous_value=position.volume,
                    new_value=0.0 if lots is None else position.volume - lots,
                    timestamp=datetime.utcnow(),
                    user=user,
                    reason=reason,
                    confirmed=confirmed,
                )
                self._record_override(record, position.symbol)

                return OverrideResult(
                    success=True,
                    message=f"Simulated close of position {position.ticket}",
                    action=OverrideAction.CLOSE_POSITION,
                    position_state=position.state.value,
                )

        except Exception as e:
            logger.error(f"Failed to close position {position.ticket}: {e}", exc_info=True)
            return OverrideResult(
                success=False,
                message=f"Failed to close position: {str(e)}",
                action=OverrideAction.CLOSE_POSITION,
                position_state=position.state.value,
            )

    async def disable_trailing_stop(
        self,
        position: TradePosition,
        user: str,
        reason: str,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Disable trailing stop for a position.

        Args:
            position: TradePosition to modify
            user: User performing the override
            reason: Reason for disabling trailing stop
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome
        """
        logger.info(
            f"Trailing stop disabled for position {position.ticket} "
            f"by user '{user}': {reason}"
        )

        # Update override state
        state = self.get_override_state(position.ticket)
        state.trailing_stopped = True

        # Record the override
        record = OverrideRecord(
            ticket=position.ticket,
            action=OverrideAction.DISABLE_TRAILING_STOP,
            previous_value=True,  # Was enabled
            new_value=False,  # Now disabled
            timestamp=datetime.utcnow(),
            user=user,
            reason=reason,
            confirmed=confirmed,
        )
        self._record_override(record, position.symbol)

        return OverrideResult(
            success=True,
            message=f"Trailing stop disabled for position {position.ticket}",
            action=OverrideAction.DISABLE_TRAILING_STOP,
            position_state=position.state.value,
        )

    async def disable_breakeven(
        self,
        position: TradePosition,
        user: str,
        reason: str,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Disable breakeven for a position.

        Args:
            position: TradePosition to modify
            user: User performing the override
            reason: Reason for disabling breakeven
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome
        """
        logger.info(
            f"Breakeven disabled for position {position.ticket} "
            f"by user '{user}': {reason}"
        )

        # Update override state
        state = self.get_override_state(position.ticket)
        state.breakeven_stopped = True

        # Record the override
        record = OverrideRecord(
            ticket=position.ticket,
            action=OverrideAction.DISABLE_BREAKEVEN,
            previous_value=True,  # Was enabled
            new_value=False,  # Now disabled
            timestamp=datetime.utcnow(),
            user=user,
            reason=reason,
            confirmed=confirmed,
        )
        self._record_override(record, position.symbol)

        return OverrideResult(
            success=True,
            message=f"Breakeven disabled for position {position.ticket}",
            action=OverrideAction.DISABLE_BREAKEVEN,
            position_state=position.state.value,
        )

    async def set_manual_stop_loss(
        self,
        position: TradePosition,
        stop_loss: float,
        user: str,
        reason: str,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Set manual stop loss for a position.

        Args:
            position: TradePosition to modify
            stop_loss: New stop loss value
            user: User performing the override
            reason: Reason for setting manual stop loss
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome
        """
        logger.info(
            f"Manual stop loss set for position {position.ticket}: "
            f"{stop_loss:.5f} by user '{user}': {reason}"
        )

        previous_sl = position.stop_loss

        try:
            # Update via MT5
            if self._mt5:
                await self._mt5.modify_position(
                    ticket=position.ticket,
                    stop_loss=stop_loss,
                )

            # Update override state
            state = self.get_override_state(position.ticket)
            state.manual_stop_loss = stop_loss

            # Update position
            position.stop_loss = stop_loss

            # Record the override
            record = OverrideRecord(
                ticket=position.ticket,
                action=OverrideAction.SET_MANUAL_STOP_LOSS,
                previous_value=previous_sl,
                new_value=stop_loss,
                timestamp=datetime.utcnow(),
                user=user,
                reason=reason,
                confirmed=confirmed,
            )
            self._record_override(record, position.symbol)

            return OverrideResult(
                success=True,
                message=f"Stop loss set to {stop_loss:.5f} for position {position.ticket}",
                action=OverrideAction.SET_MANUAL_STOP_LOSS,
                position_state=position.state.value,
            )

        except Exception as e:
            logger.error(f"Failed to set stop loss for position {position.ticket}: {e}")
            return OverrideResult(
                success=False,
                message=f"Failed to set stop loss: {str(e)}",
                action=OverrideAction.SET_MANUAL_STOP_LOSS,
                position_state=position.state.value,
            )

    async def set_manual_take_profit(
        self,
        position: TradePosition,
        take_profit: float,
        user: str,
        reason: str,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Set manual take profit for a position.

        Args:
            position: TradePosition to modify
            take_profit: New take profit value
            user: User performing the override
            reason: Reason for setting manual take profit
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome
        """
        logger.info(
            f"Manual take profit set for position {position.ticket}: "
            f"{take_profit:.5f} by user '{user}': {reason}"
        )

        previous_tp = position.take_profit

        try:
            # Update via MT5
            if self._mt5:
                await self._mt5.modify_position(
                    ticket=position.ticket,
                    take_profit=take_profit,
                )

            # Update override state
            state = self.get_override_state(position.ticket)
            state.manual_take_profit = take_profit

            # Update position
            position.take_profit = take_profit

            # Record the override
            record = OverrideRecord(
                ticket=position.ticket,
                action=OverrideAction.SET_MANUAL_TAKE_PROFIT,
                previous_value=previous_tp,
                new_value=take_profit,
                timestamp=datetime.utcnow(),
                user=user,
                reason=reason,
                confirmed=confirmed,
            )
            self._record_override(record, position.symbol)

            return OverrideResult(
                success=True,
                message=f"Take profit set to {take_profit:.5f} for position {position.ticket}",
                action=OverrideAction.SET_MANUAL_TAKE_PROFIT,
                position_state=position.state.value,
            )

        except Exception as e:
            logger.error(f"Failed to set take profit for position {position.ticket}: {e}")
            return OverrideResult(
                success=False,
                message=f"Failed to set take profit: {str(e)}",
                action=OverrideAction.SET_MANUAL_TAKE_PROFIT,
                position_state=position.state.value,
            )

    async def pause_management(
        self,
        position: TradePosition,
        user: str,
        reason: str,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Pause active management for a position.

        While paused, no automated management actions will be taken
        (trailing stop, breakeven, partial profit, etc.).

        Args:
            position: TradePosition to pause management for
            user: User performing the override
            reason: Reason for pausing management
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome
        """
        logger.info(
            f"Active management paused for position {position.ticket} "
            f"by user '{user}': {reason}"
        )

        # Update override state
        state = self.get_override_state(position.ticket)
        state.management_paused = True

        # Record the override
        record = OverrideRecord(
            ticket=position.ticket,
            action=OverrideAction.PAUSE_MANAGEMENT,
            previous_value=False,  # Was not paused
            new_value=True,  # Now paused
            timestamp=datetime.utcnow(),
            user=user,
            reason=reason,
            confirmed=confirmed,
        )
        self._record_override(record, position.symbol)

        return OverrideResult(
            success=True,
            message=f"Active management paused for position {position.ticket}",
            action=OverrideAction.PAUSE_MANAGEMENT,
            position_state=position.state.value,
        )

    async def resume_management(
        self,
        position: TradePosition,
        user: str,
        reason: str,
        confirmed: bool = False,
    ) -> OverrideResult:
        """
        Resume active management for a position.

        Args:
            position: TradePosition to resume management for
            user: User performing the override
            reason: Reason for resuming management
            confirmed: Whether the action was confirmed by user

        Returns:
            OverrideResult with operation outcome
        """
        logger.info(
            f"Active management resumed for position {position.ticket} "
            f"by user '{user}': {reason}"
        )

        # Update override state
        state = self.get_override_state(position.ticket)
        state.management_paused = False

        # Record the override
        record = OverrideRecord(
            ticket=position.ticket,
            action=OverrideAction.RESUME_MANAGEMENT,
            previous_value=True,  # Was paused
            new_value=False,  # Now resumed
            timestamp=datetime.utcnow(),
            user=user,
            reason=reason,
            confirmed=confirmed,
        )
        self._record_override(record, position.symbol)

        return OverrideResult(
            success=True,
            message=f"Active management resumed for position {position.ticket}",
            action=OverrideAction.RESUME_MANAGEMENT,
            position_state=position.state.value,
        )

    def is_management_paused(self, ticket: int) -> bool:
        """
        Check if active management is paused for a position.

        Args:
            ticket: Position ticket number

        Returns:
            True if management is paused, False otherwise
        """
        state = self.get_override_state(ticket)
        return state.management_paused

    def is_trailing_stopped(self, ticket: int) -> bool:
        """
        Check if trailing stop is disabled for a position.

        Args:
            ticket: Position ticket number

        Returns:
            True if trailing stop is disabled, False otherwise
        """
        state = self.get_override_state(ticket)
        return state.trailing_stopped

    def is_breakeven_stopped(self, ticket: int) -> bool:
        """
        Check if breakeven is disabled for a position.

        Args:
            ticket: Position ticket number

        Returns:
            True if breakeven is disabled, False otherwise
        """
        state = self.get_override_state(ticket)
        return state.breakeven_stopped

    def get_override_history(
        self, ticket: Optional[int] = None
    ) -> list[OverrideRecord]:
        """
        Get manual override history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of OverrideRecord objects
        """
        if ticket is None:
            return self._override_history.copy()
        return [r for r in self._override_history if r.ticket == ticket]

    def clear_override_history(self) -> None:
        """Clear the override history."""
        self._override_history.clear()
        logger.debug("Override history cleared")

    def clear_override_state(self, ticket: int) -> None:
        """
        Clear override state for a position (e.g., after position is closed).

        Args:
            ticket: Position ticket number
        """
        if ticket in self._override_states:
            del self._override_states[ticket]
            logger.debug(f"Override state cleared for position {ticket}")

    def _record_override(self, record: OverrideRecord, symbol: str = "UNKNOWN") -> None:
        """
        Record a manual override action.

        Args:
            record: OverrideRecord to store
            symbol: Trading symbol for the position
        """
        self._override_history.append(record)

        logger.info(
            f"Override recorded: {record.action.value} for position {record.ticket} "
            f"by user '{record.user}': {record.reason}"
        )

        # Send alert if alert system is configured
        if self._alert_system is not None:
            try:
                import asyncio
                asyncio.create_task(
                    self._alert_system.alert_manual_override_used(
                        ticket=record.ticket,
                        symbol=symbol,
                        action=record.action.value,
                        user=record.user,
                        reason=record.reason,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send manual override alert: {e}")

        # Trigger callback if registered
        if self._on_override_callback:
            try:
                self._on_override_callback(record)
            except Exception as e:
                logger.error(f"Error in override callback: {e}", exc_info=True)


# Mock MT5 connector for testing
class MT5Connector:
    """
    Mock MT5 connector for testing and development.

    In production, this would interface with the actual MetaTrader5 API.
    """

    async def close_position(
        self, ticket: int, lots: Optional[float] = None
    ) -> bool:
        """Close a position via MT5."""
        # This would call the actual MT5 API in production
        return True

    async def modify_position(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> bool:
        """Modify a position via MT5."""
        # This would call the actual MT5 API in production
        return True
