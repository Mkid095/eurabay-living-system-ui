"""
Management Alert System for active trade management notifications.

This module implements a comprehensive alert system that notifies traders
when important management actions are taken on their positions.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Any

from .trade_state import TradePosition


# Configure logging
logger = logging.getLogger(__name__)


class AlertPriority(str, Enum):
    """
    Alert priority levels.

    Attributes:
        INFO: Informational alerts (e.g., trailing stop updated)
        WARNING: Warning alerts (e.g., holding time limit reached)
        CRITICAL: Critical alerts (e.g., position closed, manual override)
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """
    Types of management alerts.

    Attributes:
        TRAILING_STOP: Trailing stop updated
        BREAKEVEN: Breakeven triggered
        PARTIAL_PROFIT: Partial profit taken
        POSITION_CLOSED: Position closed
        MANUAL_OVERRIDE: Manual override used
        HOLDING_LIMIT: Holding time limit reached
    """

    TRAILING_STOP = "trailing_stop"
    BREAKEVEN = "breakeven"
    PARTIAL_PROFIT = "partial_profit"
    POSITION_CLOSED = "position_closed"
    MANUAL_OVERRIDE = "manual_override"
    HOLDING_LIMIT = "holding_limit"


@dataclass
class Alert:
    """
    A management alert notification.

    Attributes:
        alert_id: Unique alert identifier
        alert_type: Type of alert
        priority: Alert priority level
        ticket: Position ticket number
        symbol: Trading symbol
        message: Alert message
        timestamp: When the alert was generated
        data: Additional alert-specific data
        is_sent: Whether the alert has been sent
    """

    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    ticket: int
    symbol: str
    message: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    is_sent: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary for WebSocket transmission."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "ticket": self.ticket,
            "symbol": self.symbol,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


@dataclass
class AlertDigest:
    """
    Hourly alert digest summary.

    Attributes:
        digest_id: Unique digest identifier
        start_time: Start of digest period
        end_time: End of digest period
        total_alerts: Total number of alerts in period
        alerts_by_type: Count of alerts by type
        alerts_by_priority: Count of alerts by priority
        alerts: List of alerts in the digest
    """

    digest_id: str
    start_time: datetime
    end_time: datetime
    total_alerts: int
    alerts_by_type: dict[str, int]
    alerts_by_priority: dict[str, int]
    alerts: list[Alert]

    def to_dict(self) -> dict[str, Any]:
        """Convert digest to dictionary for API response."""
        return {
            "digest_id": self.digest_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_alerts": self.total_alerts,
            "alerts_by_type": self.alerts_by_type,
            "alerts_by_priority": self.alerts_by_priority,
            "alerts": [alert.to_dict() for alert in self.alerts],
        }


class ManagementAlertSystem:
    """
    Comprehensive alert system for management actions.

    Features:
    - Real-time alerts for all management actions
    - Alert priority levels (INFO, WARNING, CRITICAL)
    - WebSocket transmission to frontend
    - Alert digest (hourly summary)
    - Alert history tracking
    - Configurable alert callbacks

    Usage:
        alert_system = ManagementAlertSystem()

        # Send an alert
        await alert_system.send_alert(
            alert_type=AlertType.TRAILING_STOP,
            ticket=12345,
            symbol="EURUSD",
            message="Trailing stop updated to 1.0850",
            priority=AlertPriority.INFO,
            data={"old_sl": 1.0840, "new_sl": 1.0850}
        )

        # Get recent alerts
        alerts = alert_system.get_recent_alerts(limit=10)

        # Get hourly digest
        digest = alert_system.get_hourly_digest()
    """

    def __init__(
        self,
        websocket_broadcast_callback: Optional[Callable[[dict], Any]] = None,
        digest_interval_minutes: int = 60,
    ):
        """
        Initialize the ManagementAlertSystem.

        Args:
            websocket_broadcast_callback: Optional callback function for WebSocket broadcasts
            digest_interval_minutes: Interval for generating alert digests (default: 60)
        """
        self._websocket_broadcast_callback = websocket_broadcast_callback
        self._digest_interval_minutes = digest_interval_minutes

        # Alert storage
        self._alerts: list[Alert] = []
        self._alerts_by_ticket: dict[int, list[Alert]] = defaultdict(list)

        # Alert counter for generating unique IDs
        self._alert_counter = 0

        # Digest tracking
        self._digest_start_time = datetime.utcnow()
        self._last_digest_time: Optional[datetime] = None

        # Start digest generation task
        self._digest_task: Optional[asyncio.Task] = None

        logger.info("ManagementAlertSystem initialized")

    async def send_alert(
        self,
        alert_type: AlertType,
        ticket: int,
        symbol: str,
        message: str,
        priority: AlertPriority = AlertPriority.INFO,
        data: Optional[dict[str, Any]] = None,
    ) -> Alert:
        """
        Send an alert for a management action.

        Args:
            alert_type: Type of alert
            ticket: Position ticket number
            symbol: Trading symbol
            message: Alert message
            priority: Alert priority level
            data: Additional alert-specific data

        Returns:
            The created Alert object
        """
        # Generate unique alert ID
        self._alert_counter += 1
        alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{self._alert_counter}"

        # Create alert
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            priority=priority,
            ticket=ticket,
            symbol=symbol,
            message=message,
            timestamp=datetime.utcnow(),
            data=data or {},
        )

        # Store alert
        self._alerts.append(alert)
        self._alerts_by_ticket[ticket].append(alert)

        # Log the alert
        logger.info(
            f"Alert sent: {alert_type.value} | Ticket: {ticket} | "
            f"Symbol: {symbol} | Priority: {priority.value} | "
            f"Message: {message}"
        )

        # Send via WebSocket if callback is available
        if self._websocket_broadcast_callback is not None:
            try:
                await self._websocket_broadcast_callback(alert.to_dict())
                alert.is_sent = True
            except Exception as e:
                logger.error(f"Failed to broadcast alert via WebSocket: {e}")

        return alert

    async def alert_trailing_stop_updated(
        self,
        ticket: int,
        symbol: str,
        old_stop_loss: float,
        new_stop_loss: float,
        current_price: float,
        profit: float,
    ) -> Alert:
        """
        Send alert when trailing stop is updated.

        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            old_stop_loss: Previous stop loss value
            new_stop_loss: New stop loss value
            current_price: Current price
            profit: Current profit

        Returns:
            The created Alert
        """
        message = (
            f"Trailing stop updated for {symbol} #{ticket}: "
            f"{old_stop_loss:.5f} -> {new_stop_loss:.5f} "
            f"(Price: {current_price:.5f}, Profit: ${profit:.2f})"
        )

        return await self.send_alert(
            alert_type=AlertType.TRAILING_STOP,
            ticket=ticket,
            symbol=symbol,
            message=message,
            priority=AlertPriority.INFO,
            data={
                "old_stop_loss": old_stop_loss,
                "new_stop_loss": new_stop_loss,
                "current_price": current_price,
                "profit": profit,
            },
        )

    async def alert_breakeven_triggered(
        self,
        ticket: int,
        symbol: str,
        stop_loss: float,
        entry_price: float,
        profit_r: float,
    ) -> Alert:
        """
        Send alert when breakeven is triggered.

        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            stop_loss: New stop loss value (at breakeven)
            entry_price: Entry price
            profit_r: Current profit in R multiples

        Returns:
            The created Alert
        """
        message = (
            f"Breakeven triggered for {symbol} #{ticket}: "
            f"Stop loss moved to {stop_loss:.5f} "
            f"(Entry: {entry_price:.5f}, Profit: {profit_r:.2f}R)"
        )

        return await self.send_alert(
            alert_type=AlertType.BREAKEVEN,
            ticket=ticket,
            symbol=symbol,
            message=message,
            priority=AlertPriority.INFO,
            data={
                "stop_loss": stop_loss,
                "entry_price": entry_price,
                "profit_r": profit_r,
            },
        )

    async def alert_partial_profit_taken(
        self,
        ticket: int,
        symbol: str,
        percentage_closed: float,
        profit_banked: float,
        remaining_volume: float,
    ) -> Alert:
        """
        Send alert when partial profit is taken.

        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            percentage_closed: Percentage of position closed
            profit_banked: Profit banked from partial close
            remaining_volume: Remaining position volume

        Returns:
            The created Alert
        """
        message = (
            f"Partial profit taken for {symbol} #{ticket}: "
            f"Closed {percentage_closed:.1f}%, Banked ${profit_banked:.2f}, "
            f"Remaining: {remaining_volume:.2f} lots"
        )

        return await self.send_alert(
            alert_type=AlertType.PARTIAL_PROFIT,
            ticket=ticket,
            symbol=symbol,
            message=message,
            priority=AlertPriority.INFO,
            data={
                "percentage_closed": percentage_closed,
                "profit_banked": profit_banked,
                "remaining_volume": remaining_volume,
            },
        )

    async def alert_position_closed(
        self,
        ticket: int,
        symbol: str,
        close_price: float,
        total_profit: float,
        reason: str,
        hold_duration_seconds: float,
    ) -> Alert:
        """
        Send alert when position is closed.

        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            close_price: Price at close
            total_profit: Total profit/loss
            reason: Reason for closure
            hold_duration_seconds: How long position was held

        Returns:
            The created Alert
        """
        # Determine if profit or loss
        profit_type = "Profit" if total_profit >= 0 else "Loss"

        # Calculate hold duration in human-readable format
        hours = hold_duration_seconds / 3600

        message = (
            f"Position closed: {symbol} #{ticket} | "
            f"{profit_type} ${abs(total_profit):.2f} | "
            f"Price: {close_price:.5f} | "
            f"Reason: {reason} | "
            f"Held: {hours:.1f}h"
        )

        # Critical priority for position closure
        return await self.send_alert(
            alert_type=AlertType.POSITION_CLOSED,
            ticket=ticket,
            symbol=symbol,
            message=message,
            priority=AlertPriority.CRITICAL,
            data={
                "close_price": close_price,
                "total_profit": total_profit,
                "reason": reason,
                "hold_duration_seconds": hold_duration_seconds,
            },
        )

    async def alert_manual_override_used(
        self,
        ticket: int,
        symbol: str,
        action: str,
        user: str,
        reason: str,
    ) -> Alert:
        """
        Send alert when manual override is used.

        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            action: Action taken (e.g., "close", "pause", "set_sl")
            user: User who performed the action
            reason: Reason for manual override

        Returns:
            The created Alert
        """
        message = (
            f"Manual override: {action.upper()} on {symbol} #{ticket} "
            f"by user '{user}' | Reason: {reason}"
        )

        # Critical priority for manual overrides
        return await self.send_alert(
            alert_type=AlertType.MANUAL_OVERRIDE,
            ticket=ticket,
            symbol=symbol,
            message=message,
            priority=AlertPriority.CRITICAL,
            data={
                "action": action,
                "user": user,
                "reason": reason,
            },
        )

    async def alert_holding_limit_reached(
        self,
        ticket: int,
        symbol: str,
        hold_duration_seconds: float,
        max_hold_duration_seconds: float,
        current_profit: float,
        action_taken: str,
    ) -> Alert:
        """
        Send alert when position hits holding time limit.

        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            hold_duration_seconds: Current hold duration
            max_hold_duration_seconds: Maximum allowed hold duration
            current_profit: Current profit/loss
            action_taken: Action taken (e.g., "closed_50%", "closed_100%")

        Returns:
            The created Alert
        """
        # Calculate hold duration in hours
        hours = hold_duration_seconds / 3600
        max_hours = max_hold_duration_seconds / 3600

        message = (
            f"Holding limit reached for {symbol} #{ticket}: "
            f"Held {hours:.1f}h (max: {max_hours:.1f}h) | "
            f"Profit: ${current_profit:.2f} | "
            f"Action: {action_taken}"
        )

        return await self.send_alert(
            alert_type=AlertType.HOLDING_LIMIT,
            ticket=ticket,
            symbol=symbol,
            message=message,
            priority=AlertPriority.WARNING,
            data={
                "hold_duration_seconds": hold_duration_seconds,
                "max_hold_duration_seconds": max_hold_duration_seconds,
                "current_profit": current_profit,
                "action_taken": action_taken,
            },
        )

    def get_recent_alerts(
        self,
        ticket: Optional[int] = None,
        alert_type: Optional[AlertType] = None,
        priority: Optional[AlertPriority] = None,
        limit: int = 100,
    ) -> list[Alert]:
        """
        Get recent alerts.

        Args:
            ticket: Filter by ticket number (optional)
            alert_type: Filter by alert type (optional)
            priority: Filter by priority level (optional)
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts matching the criteria
        """
        alerts = self._alerts

        # Apply filters
        if ticket is not None:
            alerts = self._alerts_by_ticket.get(ticket, [])

        if alert_type is not None:
            alerts = [a for a in alerts if a.alert_type == alert_type]

        if priority is not None:
            alerts = [a for a in alerts if a.priority == priority]

        # Sort by timestamp descending (most recent first)
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)

        # Apply limit
        return alerts[:limit]

    def get_alerts_since(self, since: datetime) -> list[Alert]:
        """
        Get all alerts since a specific time.

        Args:
            since: Start time for alert retrieval

        Returns:
            List of alerts since the specified time
        """
        return [a for a in self._alerts if a.timestamp >= since]

    def get_hourly_digest(self) -> AlertDigest:
        """
        Generate hourly alert digest.

        Returns:
            AlertDigest with summary of alerts in the period
        """
        now = datetime.utcnow()
        start_time = self._digest_start_time

        # Get alerts in the digest period
        period_alerts = [
            a for a in self._alerts
            if start_time <= a.timestamp < now
        ]

        # Count alerts by type
        alerts_by_type: dict[str, int] = defaultdict(int)
        for alert in period_alerts:
            alerts_by_type[alert.alert_type.value] += 1

        # Count alerts by priority
        alerts_by_priority: dict[str, int] = defaultdict(int)
        for alert in period_alerts:
            alerts_by_priority[alert.priority.value] += 1

        # Create digest
        digest_id = f"digest_{now.strftime('%Y%m%d_%H%M%S')}"
        digest = AlertDigest(
            digest_id=digest_id,
            start_time=start_time,
            end_time=now,
            total_alerts=len(period_alerts),
            alerts_by_type=dict(alerts_by_type),
            alerts_by_priority=dict(alerts_by_priority),
            alerts=period_alerts,
        )

        # Update digest start time for next period
        self._digest_start_time = now
        self._last_digest_time = now

        logger.info(
            f"Generated hourly digest: {digest_id} | "
            f"Total alerts: {len(period_alerts)} | "
            f"By type: {dict(alerts_by_type)} | "
            f"By priority: {dict(alerts_by_priority)}"
        )

        return digest

    async def start_digest_generation(self) -> None:
        """
        Start background task for generating periodic alert digests.

        Runs every digest_interval_minutes to generate and log digest summaries.
        """
        if self._digest_task is not None:
            logger.warning("Digest generation task already running")
            return

        async def digest_loop():
            """Background loop for digest generation."""
            while True:
                try:
                    # Sleep for digest interval
                    await asyncio.sleep(self._digest_interval_minutes * 60)

                    # Generate digest
                    digest = self.get_hourly_digest()

                    # Log digest summary
                    logger.info(
                        f"Alert Digest [{digest.start_time.strftime('%Y-%m-%d %H:%M')} - "
                        f"{digest.end_time.strftime('%Y-%m-%d %H:%M')}]: "
                        f"Total: {digest.total_alerts} | "
                        f"Types: {digest.alerts_by_type} | "
                        f"Priorities: {digest.alerts_by_priority}"
                    )

                except asyncio.CancelledError:
                    logger.info("Digest generation task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in digest generation: {e}")

        self._digest_task = asyncio.create_task(digest_loop())
        logger.info("Digest generation task started")

    async def stop_digest_generation(self) -> None:
        """Stop background task for generating periodic alert digests."""
        if self._digest_task is not None:
            self._digest_task.cancel()
            try:
                await self._digest_task
            except asyncio.CancelledError:
                pass
            self._digest_task = None
            logger.info("Digest generation task stopped")

    def clear_history(self, ticket: Optional[int] = None) -> None:
        """
        Clear alert history.

        Args:
            ticket: Optional ticket to clear only that position's alerts.
                   If None, clears all alert history.
        """
        if ticket is None:
            self._alerts.clear()
            self._alerts_by_ticket.clear()
            logger.info("Cleared all alert history")
        else:
            # Remove alerts for specific ticket
            self._alerts = [a for a in self._alerts if a.ticket != ticket]
            if ticket in self._alerts_by_ticket:
                del self._alerts_by_ticket[ticket]
            logger.info(f"Cleared alert history for position {ticket}")

    def get_alert_count(self, ticket: Optional[int] = None) -> int:
        """
        Get count of alerts.

        Args:
            ticket: Optional ticket to count alerts for specific position

        Returns:
            Number of alerts
        """
        if ticket is None:
            return len(self._alerts)
        return len(self._alerts_by_ticket.get(ticket, []))
