"""
Tests for TradeLifecycleLogger.

Tests comprehensive trade lifecycle event logging, database storage,
 querying, reporting, and CSV export functionality.
"""

import os
import csv
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from backend.core.trade_lifecycle_logger import (
    TradeLifecycleLogger,
    LifecycleEventType,
    MarketConditions,
    LifecycleEvent,
    ManagementAction,
)
from backend.core import TradePosition, TradeState


class TestMarketConditions(unittest.TestCase):
    """Test MarketConditions dataclass."""

    def test_market_conditions_creation(self) -> None:
        """Test creating a MarketConditions object."""
        conditions = MarketConditions(
            bid_price=1.1000,
            ask_price=1.1005,
            spread=5.0,
            atr=0.0015,
            volatility="medium",
            trend_direction="up",
            regime="trending",
        )

        self.assertEqual(conditions.bid_price, 1.1000)
        self.assertEqual(conditions.ask_price, 1.1005)
        self.assertEqual(conditions.spread, 5.0)
        self.assertEqual(conditions.atr, 0.0015)
        self.assertEqual(conditions.volatility, "medium")
        self.assertEqual(conditions.trend_direction, "up")
        self.assertEqual(conditions.regime, "trending")

    def test_market_conditions_to_dict(self) -> None:
        """Test converting MarketConditions to dictionary."""
        conditions = MarketConditions(
            bid_price=1.1000,
            ask_price=1.1005,
            spread=5.0,
        )

        data = conditions.to_dict()

        self.assertEqual(data["bid_price"], 1.1000)
        self.assertEqual(data["ask_price"], 1.1005)
        self.assertEqual(data["spread"], 5.0)
        self.assertIn("timestamp", data)


class TestLifecycleEvent(unittest.TestCase):
    """Test LifecycleEvent dataclass."""

    def test_lifecycle_event_creation(self) -> None:
        """Test creating a LifecycleEvent."""
        market_conditions = MarketConditions(
            bid_price=1.1000,
            ask_price=1.1005,
            spread=5.0,
        )

        event = LifecycleEvent(
            ticket=12345,
            event_type=LifecycleEventType.SL_UPDATE,
            timestamp=datetime.utcnow(),
            trade_state=TradeState.OPEN,
            event_data={"old_sl": 1.0950, "new_sl": 1.0980},
            market_conditions=market_conditions,
            reason="Trailing stop updated",
            profit=50.0,
            position_details={
                "symbol": "EURUSD",
                "direction": "BUY",
                "volume": 0.1,
            },
        )

        self.assertEqual(event.ticket, 12345)
        self.assertEqual(event.event_type, LifecycleEventType.SL_UPDATE)
        self.assertEqual(event.trade_state, TradeState.OPEN)
        self.assertEqual(event.profit, 50.0)
        self.assertEqual(event.reason, "Trailing stop updated")


class TestManagementAction(unittest.TestCase):
    """Test ManagementAction dataclass."""

    def test_management_action_creation(self) -> None:
        """Test creating a ManagementAction."""
        action = ManagementAction(
            ticket=12345,
            action_type="trailing_stop",
            timestamp=datetime.utcnow(),
            old_value=1.0950,
            new_value=1.0980,
            result="success",
            reason="Price moved favorably",
            executor="TrailingStopManager",
        )

        self.assertEqual(action.ticket, 12345)
        self.assertEqual(action.action_type, "trailing_stop")
        self.assertEqual(action.old_value, 1.0950)
        self.assertEqual(action.new_value, 1.0980)
        self.assertEqual(action.result, "success")
        self.assertEqual(action.executor, "TrailingStopManager")

    def test_management_action_to_dict(self) -> None:
        """Test converting ManagementAction to dictionary."""
        action = ManagementAction(
            ticket=12345,
            action_type="breakeven",
            timestamp=datetime.utcnow(),
            old_value=None,
            new_value=1.1000,
            result="success",
            reason="Breakeven triggered",
            executor="BreakevenManager",
        )

        data = action.to_dict()

        self.assertEqual(data["ticket"], 12345)
        self.assertEqual(data["action_type"], "breakeven")
        self.assertIsNone(data["old_value"])
        self.assertEqual(data["new_value"], "1.1")
        self.assertEqual(data["result"], "success")


class TestTradeLifecycleLogger(unittest.TestCase):
    """Test TradeLifecycleLogger functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a temporary database file
        self.test_db_path = "test_trade_lifecycle.db"

        # Remove existing test database if it exists
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        # Create logger instance
        self.logger = TradeLifecycleLogger(database_path=self.test_db_path)

        # Create a test position
        self.position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            current_price=1.1050,
            volume=0.1,
            stop_loss=1.0950,
            take_profit=1.1100,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            profit=50.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # Create market conditions
        self.market_conditions = MarketConditions(
            bid_price=1.1050,
            ask_price=1.1055,
            spread=5.0,
            atr=0.0015,
            volatility="low",
            trend_direction="up",
            regime="trending",
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Close logger
        self.logger.close()

        # Remove test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_logger_initialization(self) -> None:
        """Test logger initializes correctly."""
        self.assertIsNotNone(self.logger._connection)
        self.assertEqual(len(self.logger._events), 0)
        self.assertEqual(len(self.logger._actions), 0)

    def test_log_event(self) -> None:
        """Test logging a lifecycle event."""
        event = self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.SL_UPDATE,
            reason="Trailing stop updated to 1.0980",
            market_conditions=self.market_conditions,
            event_data={"old_sl": 1.0950, "new_sl": 1.0980},
        )

        self.assertEqual(event.ticket, 12345)
        self.assertEqual(event.event_type, LifecycleEventType.SL_UPDATE)
        self.assertEqual(len(self.logger._events), 1)

    def test_log_multiple_events(self) -> None:
        """Test logging multiple events for the same position."""
        # Log entry event
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        # Log SL update
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.SL_UPDATE,
            reason="Trailing stop updated",
            market_conditions=self.market_conditions,
        )

        # Log breakeven
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.BREAKEVEN,
            reason="Breakeven triggered",
            market_conditions=self.market_conditions,
        )

        self.assertEqual(len(self.logger._events), 3)

    def test_log_management_action(self) -> None:
        """Test logging a management action."""
        action = self.logger.log_management_action(
            ticket=12345,
            action_type="trailing_stop",
            old_value=1.0950,
            new_value=1.0980,
            result="success",
            reason="Price moved up 50 pips",
            executor="TrailingStopManager",
        )

        self.assertEqual(action.ticket, 12345)
        self.assertEqual(action.action_type, "trailing_stop")
        self.assertEqual(len(self.logger._actions), 1)

    def test_query_trade_history_by_ticket(self) -> None:
        """Test querying trade history by ticket."""
        # Log events for position 12345
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        # Create another position
        position2 = TradePosition(
            ticket=67890,
            symbol="GBPUSD",
            direction="SELL",
            entry_price=1.3000,
            current_price=1.2950,
            volume=0.1,
            stop_loss=1.3100,
            take_profit=1.2800,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.0,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # Log event for position 67890
        self.logger.log_event(
            position=position2,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        # Query for position 12345 only
        events = self.logger.query_trade_history(ticket=12345)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].ticket, 12345)

    def test_query_trade_history_by_event_type(self) -> None:
        """Test querying trade history by event type."""
        # Log different event types
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.SL_UPDATE,
            reason="SL updated",
            market_conditions=self.market_conditions,
        )

        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.BREAKEVEN,
            reason="Breakeven triggered",
            market_conditions=self.market_conditions,
        )

        # Query only SL_UPDATE events
        events = self.logger.query_trade_history(event_type=LifecycleEventType.SL_UPDATE)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, LifecycleEventType.SL_UPDATE)

    def test_query_trade_history_with_time_range(self) -> None:
        """Test querying trade history with time range."""
        now = datetime.utcnow()

        # Log an event
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        # Query with time range that includes the event
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=1)

        events = self.logger.query_trade_history(
            start_time=start_time,
            end_time=end_time,
        )

        self.assertGreaterEqual(len(events), 1)

    def test_query_trade_history_with_limit(self) -> None:
        """Test querying trade history with limit."""
        # Log multiple events
        for i in range(5):
            self.logger.log_event(
                position=self.position,
                event_type=LifecycleEventType.SL_UPDATE,
                reason=f"SL update {i}",
                market_conditions=self.market_conditions,
            )

        # Query with limit
        events = self.logger.query_trade_history(ticket=12345, limit=3)

        self.assertEqual(len(events), 3)

    def test_generate_lifecycle_report(self) -> None:
        """Test generating a lifecycle report."""
        # Log some events
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened at 1.1000",
            market_conditions=self.market_conditions,
        )

        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.SL_UPDATE,
            reason="Trailing stop updated to 1.0980",
            market_conditions=self.market_conditions,
        )

        # Generate report
        report = self.logger.generate_lifecycle_report(ticket=12345)

        self.assertIn("TRADE LIFECYCLE REPORT", report)
        self.assertIn("Position 12345", report)
        self.assertIn("Total Events: 2", report)
        self.assertIn("entry", report)
        self.assertIn("sl_update", report)

    def test_generate_lifecycle_report_no_events(self) -> None:
        """Test generating report when no events exist."""
        report = self.logger.generate_lifecycle_report(ticket=99999)

        self.assertIn("No lifecycle events found", report)

    def test_export_to_csv(self) -> None:
        """Test exporting lifecycle data to CSV."""
        # Log some events
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.SL_UPDATE,
            reason="Trailing stop updated",
            market_conditions=self.market_conditions,
        )

        # Export to CSV
        csv_path = "test_lifecycle_export.csv"

        try:
            self.logger.export_to_csv(filepath=csv_path, ticket=12345)

            # Verify file was created
            self.assertTrue(os.path.exists(csv_path))

            # Read and verify CSV content
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["ticket"], "12345")
                self.assertEqual(rows[0]["event_type"], "entry")
                self.assertEqual(rows[1]["event_type"], "sl_update")

        finally:
            # Clean up CSV file
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_export_to_csv_with_filters(self) -> None:
        """Test exporting to CSV with filters."""
        # Log events for different positions
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        position2 = TradePosition(
            ticket=67890,
            symbol="GBPUSD",
            direction="SELL",
            entry_price=1.3000,
            current_price=1.2950,
            volume=0.1,
            stop_loss=1.3100,
            take_profit=1.2800,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.0,
            commission=1.0,
            state=TradeState.OPEN,
        )

        self.logger.log_event(
            position=position2,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        # Export only position 12345
        csv_path = "test_lifecycle_filtered.csv"

        try:
            self.logger.export_to_csv(filepath=csv_path, ticket=12345)

            # Verify only one position exported
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["ticket"], "12345")

        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_get_management_actions(self) -> None:
        """Test retrieving management actions."""
        # Log some actions
        self.logger.log_management_action(
            ticket=12345,
            action_type="trailing_stop",
            old_value=1.0950,
            new_value=1.0980,
            result="success",
            reason="Price moved up",
            executor="TrailingStopManager",
        )

        self.logger.log_management_action(
            ticket=12345,
            action_type="breakeven",
            old_value=1.0980,
            new_value=1.1005,
            result="success",
            reason="Breakeven triggered",
            executor="BreakevenManager",
        )

        # Get all actions
        actions = self.logger.get_management_actions(ticket=12345)

        self.assertEqual(len(actions), 2)

    def test_get_management_actions_by_type(self) -> None:
        """Test filtering management actions by type."""
        # Log different action types
        self.logger.log_management_action(
            ticket=12345,
            action_type="trailing_stop",
            old_value=1.0950,
            new_value=1.0980,
            result="success",
            reason="Price moved up",
            executor="TrailingStopManager",
        )

        self.logger.log_management_action(
            ticket=12345,
            action_type="breakeven",
            old_value=1.0980,
            new_value=1.1005,
            result="success",
            reason="Breakeven triggered",
            executor="BreakevenManager",
        )

        # Get only trailing_stop actions
        actions = self.logger.get_management_actions(
            ticket=12345,
            action_type="trailing_stop",
        )

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action_type, "trailing_stop")

    def test_clear_history_all(self) -> None:
        """Test clearing all history."""
        # Log some events
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        self.logger.log_management_action(
            ticket=12345,
            action_type="trailing_stop",
            old_value=1.0950,
            new_value=1.0980,
            result="success",
            reason="Price moved up",
            executor="TrailingStopManager",
        )

        # Clear all history
        self.logger.clear_history()

        self.assertEqual(len(self.logger._events), 0)
        self.assertEqual(len(self.logger._actions), 0)

    def test_clear_history_by_ticket(self) -> None:
        """Test clearing history for a specific ticket."""
        # Log events for two positions
        self.logger.log_event(
            position=self.position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        position2 = TradePosition(
            ticket=67890,
            symbol="GBPUSD",
            direction="SELL",
            entry_price=1.3000,
            current_price=1.2950,
            volume=0.1,
            stop_loss=1.3100,
            take_profit=1.2800,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.0,
            commission=1.0,
            state=TradeState.OPEN,
        )

        self.logger.log_event(
            position=position2,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened",
            market_conditions=self.market_conditions,
        )

        # Clear only position 12345
        self.logger.clear_history(ticket=12345)

        # Should have 1 event remaining (for position 67890)
        self.assertEqual(len(self.logger._events), 1)
        self.assertEqual(self.logger._events[0].ticket, 67890)

    def test_lifecycle_event_types(self) -> None:
        """Test all lifecycle event types."""
        event_types = [
            LifecycleEventType.ENTRY,
            LifecycleEventType.SL_UPDATE,
            LifecycleEventType.TP_UPDATE,
            LifecycleEventType.PARTIAL_CLOSE,
            LifecycleEventType.FULL_CLOSE,
            LifecycleEventType.BREAKEVEN,
            LifecycleEventType.TRAILING_STOP,
            LifecycleEventType.SCALE_IN,
            LifecycleEventType.SCALE_OUT,
            LifecycleEventType.HOLDING_LIMIT,
            LifecycleEventType.MANUAL_OVERRIDE,
            LifecycleEventType.STATE_CHANGE,
            LifecycleEventType.MANAGEMENT_ACTION,
        ]

        for event_type in event_types:
            event = self.logger.log_event(
                position=self.position,
                event_type=event_type,
                reason=f"Test {event_type.value}",
                market_conditions=self.market_conditions,
            )

            self.assertEqual(event.event_type, event_type)


class TestLifecycleEventIntegration(unittest.TestCase):
    """Integration tests for lifecycle logging with trade management."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.test_db_path = "test_integration_lifecycle.db"

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.logger = TradeLifecycleLogger(database_path=self.test_db_path)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.logger.close()

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_full_trade_lifecycle(self) -> None:
        """Test logging a complete trade lifecycle."""
        # Create initial position
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            current_price=1.1000,
            volume=0.1,
            stop_loss=1.0950,
            take_profit=1.1100,
            entry_time=datetime.utcnow(),
            profit=0.0,
            swap=0.0,
            commission=1.0,
            state=TradeState.OPEN,
        )

        market_conditions = MarketConditions(
            bid_price=1.1000,
            ask_price=1.1005,
            spread=5.0,
            volatility="low",
            trend_direction="up",
            regime="trending",
        )

        # Log entry
        self.logger.log_event(
            position=position,
            event_type=LifecycleEventType.ENTRY,
            reason="Position opened at market",
            market_conditions=market_conditions,
        )

        # Simulate price movement and trailing stop
        position.current_price = 1.1050
        position.profit = 50.0

        self.logger.log_event(
            position=position,
            event_type=LifecycleEventType.TRAILING_STOP,
            reason="Trailing stop updated to 1.0980",
            market_conditions=market_conditions,
            event_data={"old_sl": 1.0950, "new_sl": 1.0980},
        )

        # Simulate breakeven
        position.current_price = 1.1075
        position.profit = 75.0
        position.stop_loss = 1.1005

        self.logger.log_event(
            position=position,
            event_type=LifecycleEventType.BREAKEVEN,
            reason="Breakeven triggered at 1.5R",
            market_conditions=market_conditions,
        )

        # Simulate partial profit
        position.current_price = 1.1100
        position.profit = 100.0

        self.logger.log_event(
            position=position,
            event_type=LifecycleEventType.PARTIAL_CLOSE,
            reason="Partial profit taken: 50% at 2R",
            market_conditions=market_conditions,
            event_data={"percentage": 50, "profit_banked": 50.0},
        )

        # Simulate full close
        position.current_price = 1.1150
        position.profit = 150.0
        position.state = TradeState.CLOSED

        self.logger.log_event(
            position=position,
            event_type=LifecycleEventType.FULL_CLOSE,
            reason="Position closed at take profit",
            market_conditions=market_conditions,
        )

        # Verify all events were logged
        events = self.logger.query_trade_history(ticket=12345)
        self.assertEqual(len(events), 5)

        # Generate and verify report
        report = self.logger.generate_lifecycle_report(ticket=12345)
        self.assertIn("Total Events: 5", report)
        self.assertIn("entry", report)
        self.assertIn("trailing_stop", report)
        self.assertIn("breakeven", report)
        self.assertIn("partial_close", report)
        self.assertIn("full_close", report)


if __name__ == "__main__":
    unittest.main()
