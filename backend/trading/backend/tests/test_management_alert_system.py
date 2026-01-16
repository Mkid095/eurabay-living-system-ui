"""
Unit tests for ManagementAlertSystem.

This module tests the alert system functionality including:
- Alert generation for all management actions
- Alert priority levels
- Alert transmission via WebSocket
- Alert digest generation
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path

# Add the core module to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from core.management_alert_system import (
    ManagementAlertSystem,
    Alert,
    AlertPriority,
    AlertType,
    AlertDigest,
)


class TestManagementAlertSystem:
    """Test suite for ManagementAlertSystem."""

    @pytest.fixture
    def mock_websocket_callback(self):
        """Create a mock WebSocket broadcast callback."""
        callback = AsyncMock()
        return callback

    @pytest.fixture
    def alert_system(self, mock_websocket_callback):
        """Create a ManagementAlertSystem instance with mock callback."""
        return ManagementAlertSystem(
            websocket_broadcast_callback=mock_websocket_callback,
            digest_interval_minutes=60,
        )

    @pytest.mark.asyncio
    async def test_send_alert(self, alert_system, mock_websocket_callback):
        """Test sending a basic alert."""
        alert = await alert_system.send_alert(
            alert_type=AlertType.TRAILING_STOP,
            ticket=12345,
            symbol="EURUSD",
            message="Trailing stop updated",
            priority=AlertPriority.INFO,
            data={"old_sl": 1.0840, "new_sl": 1.0850},
        )

        # Verify alert was created
        assert alert.alert_id.startswith("alert_")
        assert alert.alert_type == AlertType.TRAILING_STOP
        assert alert.ticket == 12345
        assert alert.symbol == "EURUSD"
        assert alert.message == "Trailing stop updated"
        assert alert.priority == AlertPriority.INFO
        assert alert.data == {"old_sl": 1.0840, "new_sl": 1.0850}
        assert alert.is_sent is True  # Should be sent via WebSocket

        # Verify WebSocket callback was called
        mock_websocket_callback.assert_called_once()
        call_args = mock_websocket_callback.call_args[0][0]
        assert call_args["alert_type"] == "trailing_stop"
        assert call_args["ticket"] == 12345

    @pytest.mark.asyncio
    async def test_alert_trailing_stop_updated(self, alert_system):
        """Test alert for trailing stop update."""
        alert = await alert_system.alert_trailing_stop_updated(
            ticket=12345,
            symbol="EURUSD",
            old_stop_loss=1.0840,
            new_stop_loss=1.0850,
            current_price=1.0860,
            profit=150.0,
        )

        assert alert.alert_type == AlertType.TRAILING_STOP
        assert alert.priority == AlertPriority.INFO
        assert "Trailing stop updated" in alert.message
        assert "1.0840 -> 1.0850" in alert.message
        assert alert.data["old_stop_loss"] == 1.0840
        assert alert.data["new_stop_loss"] == 1.0850

    @pytest.mark.asyncio
    async def test_alert_breakeven_triggered(self, alert_system):
        """Test alert for breakeven trigger."""
        alert = await alert_system.alert_breakeven_triggered(
            ticket=12346,
            symbol="GBPUSD",
            stop_loss=1.2650,
            entry_price=1.2650,
            profit_r=1.5,
        )

        assert alert.alert_type == AlertType.BREAKEVEN
        assert alert.priority == AlertPriority.INFO
        assert "Breakeven triggered" in alert.message
        assert alert.data["stop_loss"] == 1.2650
        assert alert.data["profit_r"] == 1.5

    @pytest.mark.asyncio
    async def test_alert_partial_profit_taken(self, alert_system):
        """Test alert for partial profit taken."""
        alert = await alert_system.alert_partial_profit_taken(
            ticket=12347,
            symbol="USDJPY",
            percentage_closed=50.0,
            profit_banked=250.0,
            remaining_volume=0.5,
        )

        assert alert.alert_type == AlertType.PARTIAL_PROFIT
        assert alert.priority == AlertPriority.INFO
        assert "Partial profit taken" in alert.message
        assert "Closed 50.0%" in alert.message
        assert "Banked $250.00" in alert.message
        assert alert.data["percentage_closed"] == 50.0
        assert alert.data["profit_banked"] == 250.0

    @pytest.mark.asyncio
    async def test_alert_position_closed(self, alert_system):
        """Test alert for position closed."""
        alert = await alert_system.alert_position_closed(
            ticket=12348,
            symbol="EURUSD",
            close_price=1.0870,
            total_profit=500.0,
            reason="Take profit hit",
            hold_duration_seconds=7200,  # 2 hours
        )

        assert alert.alert_type == AlertType.POSITION_CLOSED
        assert alert.priority == AlertPriority.CRITICAL
        assert "Position closed" in alert.message
        assert "Profit $500.00" in alert.message
        assert "Held: 2.0h" in alert.message
        assert alert.data["close_price"] == 1.0870
        assert alert.data["total_profit"] == 500.0

    @pytest.mark.asyncio
    async def test_alert_manual_override_used(self, alert_system):
        """Test alert for manual override."""
        alert = await alert_system.alert_manual_override_used(
            ticket=12349,
            symbol="GBPUSD",
            action="close",
            user="trader1",
            reason="Taking manual profit",
        )

        assert alert.alert_type == AlertType.MANUAL_OVERRIDE
        assert alert.priority == AlertPriority.CRITICAL
        assert "Manual override" in alert.message
        assert "CLOSE" in alert.message
        assert "trader1" in alert.message
        assert alert.data["action"] == "close"
        assert alert.data["user"] == "trader1"

    @pytest.mark.asyncio
    async def test_alert_holding_limit_reached(self, alert_system):
        """Test alert for holding time limit reached."""
        alert = await alert_system.alert_holding_limit_reached(
            ticket=12350,
            symbol="USDJPY",
            hold_duration_seconds=14400,  # 4 hours
            max_hold_duration_seconds=7200,  # 2 hours max
            current_profit=100.0,
            action_taken="closed_50%",
        )

        assert alert.alert_type == AlertType.HOLDING_LIMIT
        assert alert.priority == AlertPriority.WARNING
        assert "Holding limit reached" in alert.message
        assert "Held 4.0h" in alert.message
        assert "closed_50%" in alert.message
        assert alert.data["hold_duration_seconds"] == 14400
        assert alert.data["max_hold_duration_seconds"] == 7200

    def test_get_recent_alerts(self, alert_system):
        """Test retrieving recent alerts."""
        # Create some test alerts
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Alert 1",
                priority=AlertPriority.INFO,
            )
        )
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.BREAKEVEN,
                ticket=12346,
                symbol="GBPUSD",
                message="Alert 2",
                priority=AlertPriority.INFO,
            )
        )

        # Run the tasks
        asyncio.run(asyncio.sleep(0.1))

        # Get recent alerts
        alerts = alert_system.get_recent_alerts(limit=10)

        assert len(alerts) == 2
        assert alerts[0].ticket == 12346  # Most recent first
        assert alerts[1].ticket == 12345

    def test_get_alerts_by_ticket(self, alert_system):
        """Test filtering alerts by ticket."""
        # Create alerts for different tickets
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Alert for 12345",
                priority=AlertPriority.INFO,
            )
        )
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.BREAKEVEN,
                ticket=12346,
                symbol="GBPUSD",
                message="Alert for 12346",
                priority=AlertPriority.INFO,
            )
        )

        asyncio.run(asyncio.sleep(0.1))

        # Get alerts for specific ticket
        alerts = alert_system.get_recent_alerts(ticket=12345)

        assert len(alerts) == 1
        assert alerts[0].ticket == 12345
        assert "12345" in alerts[0].message

    def test_get_alerts_by_priority(self, alert_system):
        """Test filtering alerts by priority."""
        # Create alerts with different priorities
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Info alert",
                priority=AlertPriority.INFO,
            )
        )
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.POSITION_CLOSED,
                ticket=12346,
                symbol="GBPUSD",
                message="Critical alert",
                priority=AlertPriority.CRITICAL,
            )
        )

        asyncio.run(asyncio.sleep(0.1))

        # Get alerts with CRITICAL priority
        alerts = alert_system.get_recent_alerts(priority=AlertPriority.CRITICAL)

        assert len(alerts) == 1
        assert alerts[0].priority == AlertPriority.CRITICAL
        assert "Critical" in alerts[0].message

    def test_get_hourly_digest(self, alert_system):
        """Test generating hourly alert digest."""
        # Create some alerts
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Alert 1",
                priority=AlertPriority.INFO,
            )
        )
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.BREAKEVEN,
                ticket=12346,
                symbol="GBPUSD",
                message="Alert 2",
                priority=AlertPriority.INFO,
            )
        )

        asyncio.run(asyncio.sleep(0.1))

        # Generate digest
        digest = alert_system.get_hourly_digest()

        assert digest.total_alerts == 2
        assert digest.alerts_by_type["trailing_stop"] == 1
        assert digest.alerts_by_type["breakeven"] == 1
        assert digest.alerts_by_priority["info"] == 2
        assert len(digest.alerts) == 2

    def test_clear_history(self, alert_system):
        """Test clearing alert history."""
        # Create an alert
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Test alert",
                priority=AlertPriority.INFO,
            )
        )

        asyncio.run(asyncio.sleep(0.1))

        # Verify alert exists
        assert alert_system.get_alert_count() == 1

        # Clear history
        alert_system.clear_history()

        # Verify history is cleared
        assert alert_system.get_alert_count() == 0

    def test_clear_history_by_ticket(self, alert_system):
        """Test clearing alert history for specific ticket."""
        # Create alerts for different tickets
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Alert for 12345",
                priority=AlertPriority.INFO,
            )
        )
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.BREAKEVEN,
                ticket=12346,
                symbol="GBPUSD",
                message="Alert for 12346",
                priority=AlertPriority.INFO,
            )
        )

        asyncio.run(asyncio.sleep(0.1))

        # Verify both alerts exist
        assert alert_system.get_alert_count() == 2

        # Clear history for specific ticket
        alert_system.clear_history(ticket=12345)

        # Verify only one alert remains
        assert alert_system.get_alert_count() == 1
        assert alert_system.get_alert_count(ticket=12345) == 0
        assert alert_system.get_alert_count(ticket=12346) == 1

    def test_get_alert_count(self, alert_system):
        """Test getting alert count."""
        # Initially no alerts
        assert alert_system.get_alert_count() == 0

        # Create an alert
        asyncio.create_task(
            alert_system.send_alert(
                alert_type=AlertType.TRAILING_STOP,
                ticket=12345,
                symbol="EURUSD",
                message="Test alert",
                priority=AlertPriority.INFO,
            )
        )

        asyncio.run(asyncio.sleep(0.1))

        # Verify count
        assert alert_system.get_alert_count() == 1
        assert alert_system.get_alert_count(ticket=12345) == 1
        assert alert_system.get_alert_count(ticket=99999) == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
