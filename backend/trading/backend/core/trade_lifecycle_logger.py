"""
Trade Lifecycle Logger for comprehensive trade event logging.

This module implements detailed logging of all trade lifecycle events
for analysis, debugging, and performance tracking.
"""

import csv
import logging
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field

from .trade_state import TradePosition, TradeState


# Configure logging
logger = logging.getLogger(__name__)


class LifecycleEventType(Enum):
    """
    Types of lifecycle events that can occur during trade management.

    Events:
        ENTRY: Position opened
        SL_UPDATE: Stop loss modified
        TP_UPDATE: Take profit modified
        PARTIAL_CLOSE: Portion of position closed
        FULL_CLOSE: Position fully closed
        BREAKEVEN: Stop loss moved to breakeven
        TRAILING_STOP: Trailing stop updated
        SCALE_IN: Position size increased
        SCALE_OUT: Position size decreased
        HOLDING_LIMIT: Holding time limit reached
        MANUAL_OVERRIDE: Manual intervention
        STATE_CHANGE: Trade state changed
        MANAGEMENT_ACTION: Any active management action
    """

    ENTRY = "entry"
    SL_UPDATE = "sl_update"
    TP_UPDATE = "tp_update"
    PARTIAL_CLOSE = "partial_close"
    FULL_CLOSE = "full_close"
    BREAKEVEN = "breakeven"
    TRAILING_STOP = "trailing_stop"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    HOLDING_LIMIT = "holding_limit"
    MANUAL_OVERRIDE = "manual_override"
    STATE_CHANGE = "state_change"
    MANAGEMENT_ACTION = "management_action"


@dataclass
class MarketConditions:
    """
    Market conditions at the time of a lifecycle event.

    Attributes:
        bid_price: Current bid price
        ask_price: Current ask price
        spread: Current spread in points
        atr: Current ATR value (if available)
        volatility: Market volatility level (low, medium, high)
        trend_direction: Current trend direction (up, down, sideways)
        regime: Market regime (trending, ranging, volatile)
        timestamp: When these conditions were captured
    """

    bid_price: float
    ask_price: float
    spread: float
    atr: Optional[float] = None
    volatility: str = "medium"
    trend_direction: str = "sideways"
    regime: str = "ranging"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "spread": self.spread,
            "atr": self.atr,
            "volatility": self.volatility,
            "trend_direction": self.trend_direction,
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class LifecycleEvent:
    """
    A single lifecycle event in a trade's history.

    Attributes:
        ticket: Position ticket number
        event_type: Type of event that occurred
        timestamp: When the event occurred
        trade_state: Trade state at the time of event
        event_data: Additional event-specific data
        market_conditions: Market conditions at time of event
        reason: Human-readable reason for the event
        profit: Profit/loss at time of event
        position_details: Snapshot of position details
    """

    ticket: int
    event_type: LifecycleEventType
    timestamp: datetime
    trade_state: TradeState
    event_data: dict[str, Any]
    market_conditions: MarketConditions
    reason: str
    profit: float
    position_details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for database storage."""
        return {
            "ticket": self.ticket,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "trade_state": self.trade_state.value,
            "event_data": str(self.event_data),
            "market_conditions": str(self.market_conditions.to_dict()),
            "reason": self.reason,
            "profit": self.profit,
            "position_details": str(self.position_details),
        }


@dataclass
class ManagementAction:
    """
    Record of a management action taken on a position.

    Attributes:
        ticket: Position ticket number
        action_type: Type of management action
        timestamp: When the action was taken
        old_value: Value before action (if applicable)
        new_value: Value after action (if applicable)
        result: Result of the action (success, failure, partial)
        reason: Why the action was taken
        executor: What system/component executed the action
    """

    ticket: int
    action_type: str
    timestamp: datetime
    old_value: Optional[float]
    new_value: Optional[float]
    result: str
    reason: str
    executor: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "ticket": self.ticket,
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat(),
            "old_value": str(self.old_value) if self.old_value is not None else None,
            "new_value": str(self.new_value) if self.new_value is not None else None,
            "result": self.result,
            "reason": self.reason,
            "executor": self.executor,
        }


class TradeLifecycleLogger:
    """
    Comprehensive logger for trade lifecycle events.

    Features:
    - Logs all trade events with timestamps
    - Captures trade state at each event
    - Records management actions taken
    - Stores market conditions at time of action
    - Persists all lifecycle events to database
    - Queries trade history
    - Generates lifecycle reports (timeline view)
    - Exports lifecycle data to CSV

    Usage:
        logger = TradeLifecycleLogger(database_path="trades.db")

        # Log an event
        logger.log_event(
            position=position,
            event_type=LifecycleEventType.SL_UPDATE,
            reason="Trailing stop updated",
            market_conditions=market_conditions
        )

        # Query history
        history = logger.query_trade_history(ticket=12345)

        # Generate report
        report = logger.generate_lifecycle_report(ticket=12345)

        # Export to CSV
        logger.export_to_csv(filepath="trade_history.csv")
    """

    def __init__(self, database_path: str = "trade_lifecycle.db"):
        """
        Initialize the TradeLifecycleLogger.

        Args:
            database_path: Path to SQLite database file
        """
        self._database_path = database_path
        self._events: list[LifecycleEvent] = []
        self._actions: list[ManagementAction] = []
        self._connection: Optional[sqlite3.Connection] = None

        # Initialize database
        self._initialize_database()

        logger.info(f"TradeLifecycleLogger initialized with database: {database_path}")

    def _initialize_database(self) -> None:
        """
        Initialize the SQLite database with required tables.

        Creates tables for:
        - lifecycle_events: All trade events
        - management_actions: All management actions
        - trade_snapshots: Position state snapshots
        """
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create lifecycle_events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    trade_state TEXT NOT NULL,
                    event_data TEXT,
                    market_conditions TEXT,
                    reason TEXT,
                    profit REAL,
                    position_details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create management_actions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS management_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    result TEXT NOT NULL,
                    reason TEXT,
                    executor TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_ticket
                ON lifecycle_events(ticket)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON lifecycle_events(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_ticket
                ON management_actions(ticket)
            """)

            self._connection.commit()

            logger.info("Database tables initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def log_event(
        self,
        position: TradePosition,
        event_type: LifecycleEventType,
        reason: str,
        market_conditions: MarketConditions,
        event_data: Optional[dict[str, Any]] = None,
    ) -> LifecycleEvent:
        """
        Log a lifecycle event for a position.

        Args:
            position: TradePosition the event is for
            event_type: Type of event that occurred
            reason: Human-readable reason for the event
            market_conditions: Market conditions at time of event
            event_data: Additional event-specific data

        Returns:
            The created LifecycleEvent
        """
        # Create position details snapshot
        position_details = {
            "symbol": position.symbol,
            "direction": position.direction,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "volume": position.volume,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "entry_time": position.entry_time.isoformat(),
            "swap": position.swap,
            "commission": position.commission,
        }

        # Create event
        event = LifecycleEvent(
            ticket=position.ticket,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            trade_state=position.state,
            event_data=event_data or {},
            market_conditions=market_conditions,
            reason=reason,
            profit=position.profit,
            position_details=position_details,
        )

        # Store in memory
        self._events.append(event)

        # Store in database
        self._store_event_in_database(event)

        # Log the event
        logger.info(
            f"Lifecycle event logged for position {position.ticket}: "
            f"{event_type.value} | State: {position.state.value} | "
            f"Reason: {reason} | Profit: {position.profit:.2f}"
        )

        return event

    def log_management_action(
        self,
        ticket: int,
        action_type: str,
        old_value: Optional[float],
        new_value: Optional[float],
        result: str,
        reason: str,
        executor: str,
    ) -> ManagementAction:
        """
        Log a management action taken on a position.

        Args:
            ticket: Position ticket number
            action_type: Type of management action (e.g., "trailing_stop", "breakeven")
            old_value: Value before action
            new_value: Value after action
            result: Result of the action (success, failure, partial)
            reason: Why the action was taken
            executor: What system executed the action

        Returns:
            The created ManagementAction
        """
        action = ManagementAction(
            ticket=ticket,
            action_type=action_type,
            timestamp=datetime.utcnow(),
            old_value=old_value,
            new_value=new_value,
            result=result,
            reason=reason,
            executor=executor,
        )

        # Store in memory
        self._actions.append(action)

        # Store in database
        self._store_action_in_database(action)

        # Log the action
        logger.info(
            f"Management action logged for position {ticket}: "
            f"{action_type} | {old_value} -> {new_value} | "
            f"Result: {result} | Executor: {executor}"
        )

        return action

    def _store_event_in_database(self, event: LifecycleEvent) -> None:
        """
        Store a lifecycle event in the database.

        Args:
            event: LifecycleEvent to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, event not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO lifecycle_events (
                    ticket, event_type, timestamp, trade_state,
                    event_data, market_conditions, reason, profit, position_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.ticket,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.trade_state.value,
                str(event.event_data),
                str(event.market_conditions.to_dict()),
                event.reason,
                event.profit,
                str(event.position_details),
            ))

            self._connection.commit()

            logger.debug(f"Event stored in database for position {event.ticket}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store event in database: {e}")

    def _store_action_in_database(self, action: ManagementAction) -> None:
        """
        Store a management action in the database.

        Args:
            action: ManagementAction to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, action not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT INTO management_actions (
                    ticket, action_type, timestamp, old_value,
                    new_value, result, reason, executor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.ticket,
                action.action_type,
                action.timestamp.isoformat(),
                str(action.old_value) if action.old_value is not None else None,
                str(action.new_value) if action.new_value is not None else None,
                action.result,
                action.reason,
                action.executor,
            ))

            self._connection.commit()

            logger.debug(f"Action stored in database for position {action.ticket}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store action in database: {e}")

    def query_trade_history(
        self,
        ticket: Optional[int] = None,
        event_type: Optional[LifecycleEventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[LifecycleEvent]:
        """
        Query trade history from the database.

        Args:
            ticket: Filter by position ticket (optional)
            event_type: Filter by event type (optional)
            start_time: Filter by start time (optional)
            end_time: Filter by end time (optional)
            limit: Maximum number of events to return (optional)

        Returns:
            List of LifecycleEvent records matching the criteria
        """
        if self._connection is None:
            logger.warning("Database connection not available, returning in-memory events")
            return self._filter_in_memory_events(ticket, event_type, start_time, end_time, limit)

        try:
            cursor = self._connection.cursor()

            # Build query
            query = "SELECT * FROM lifecycle_events WHERE 1=1"
            params: list[Any] = []

            if ticket is not None:
                query += " AND ticket = ?"
                params.append(ticket)

            if event_type is not None:
                query += " AND event_type = ?"
                params.append(event_type.value)

            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC"

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)

            # Convert rows to LifecycleEvent objects
            events = []
            for row in cursor.fetchall():
                # Parse row data and create LifecycleEvent
                # This is a simplified version - in production, you'd parse properly
                events.append(self._row_to_lifecycle_event(row))

            logger.info(f"Queried {len(events)} lifecycle events from database")

            return events

        except sqlite3.Error as e:
            logger.error(f"Failed to query trade history: {e}")
            return []

    def _filter_in_memory_events(
        self,
        ticket: Optional[int],
        event_type: Optional[LifecycleEventType],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: Optional[int],
    ) -> list[LifecycleEvent]:
        """
        Filter in-memory events when database is not available.

        Args:
            ticket: Filter by position ticket
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events to return

        Returns:
            Filtered list of LifecycleEvent records
        """
        events = self._events

        # Apply filters
        if ticket is not None:
            events = [e for e in events if e.ticket == ticket]

        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]

        if start_time is not None:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time is not None:
            events = [e for e in events if e.timestamp <= end_time]

        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        if limit is not None:
            events = events[:limit]

        return events

    def _row_to_lifecycle_event(self, row: tuple) -> LifecycleEvent:
        """
        Convert a database row to a LifecycleEvent object.

        Args:
            row: Database row tuple

        Returns:
            LifecycleEvent object
        """
        # This is a simplified conversion
        # In production, you'd properly parse the stored JSON strings
        return LifecycleEvent(
            ticket=row[1],
            event_type=LifecycleEventType(row[2]),
            timestamp=datetime.fromisoformat(row[3]),
            trade_state=TradeState(row[4]),
            event_data={},
            market_conditions=MarketConditions(
                bid_price=0.0,
                ask_price=0.0,
                spread=0.0,
            ),
            reason=row[7],
            profit=row[8],
            position_details={},
        )

    def generate_lifecycle_report(self, ticket: int) -> str:
        """
        Generate a lifecycle report for a position (timeline view).

        Args:
            ticket: Position ticket number

        Returns:
            Formatted timeline report string
        """
        # Use in-memory events for the report to ensure all data is available
        events = [e for e in self._events if e.ticket == ticket]

        if not events:
            return f"No lifecycle events found for position {ticket}"

        # Sort events by timestamp ascending for timeline
        events_sorted = sorted(events, key=lambda e: e.timestamp)

        # Build report
        lines = [
            f"=" * 80,
            f"TRADE LIFECYCLE REPORT - Position {ticket}",
            f"=" * 80,
            "",
            f"Total Events: {len(events_sorted)}",
            "",
            "TIMELINE:",
            "-" * 80,
        ]

        for i, event in enumerate(events_sorted, 1):
            lines.extend([
                "",
                f"Event {i}:",
                f"  Type: {event.event_type.value}",
                f"  Time: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"  State: {event.trade_state.value}",
                f"  Reason: {event.reason}",
                f"  Profit: {event.profit:.2f}",
                f"  Market Conditions:",
                f"    Bid: {event.market_conditions.bid_price:.5f}",
                f"    Ask: {event.market_conditions.ask_price:.5f}",
                f"    Spread: {event.market_conditions.spread:.1f}",
                f"    Regime: {event.market_conditions.regime}",
            ])

            if event.event_data:
                lines.append(f"  Event Data: {event.event_data}")

        lines.extend([
            "",
            "=" * 80,
        ])

        report = "\n".join(lines)

        logger.info(f"Generated lifecycle report for position {ticket}")

        return report

    def export_to_csv(
        self,
        filepath: str,
        ticket: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """
        Export lifecycle data to CSV file.

        Args:
            filepath: Path to output CSV file
            ticket: Filter by position ticket (optional)
            start_time: Filter by start time (optional)
            end_time: Filter by end time (optional)
        """
        # Query events
        events = self.query_trade_history(
            ticket=ticket,
            start_time=start_time,
            end_time=end_time,
        )

        if not events:
            logger.warning("No events to export")
            return

        # Sort by timestamp ascending
        events_sorted = sorted(events, key=lambda e: e.timestamp)

        # Write to CSV
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "ticket",
                    "event_type",
                    "timestamp",
                    "trade_state",
                    "reason",
                    "profit",
                    "bid_price",
                    "ask_price",
                    "spread",
                    "volatility",
                    "regime",
                    "symbol",
                    "direction",
                    "entry_price",
                    "current_price",
                    "volume",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for event in events_sorted:
                    writer.writerow({
                        "ticket": event.ticket,
                        "event_type": event.event_type.value,
                        "timestamp": event.timestamp.isoformat(),
                        "trade_state": event.trade_state.value,
                        "reason": event.reason,
                        "profit": event.profit,
                        "bid_price": event.market_conditions.bid_price,
                        "ask_price": event.market_conditions.ask_price,
                        "spread": event.market_conditions.spread,
                        "volatility": event.market_conditions.volatility,
                        "regime": event.market_conditions.regime,
                        "symbol": event.position_details.get("symbol", ""),
                        "direction": event.position_details.get("direction", ""),
                        "entry_price": event.position_details.get("entry_price", 0.0),
                        "current_price": event.position_details.get("current_price", 0.0),
                        "volume": event.position_details.get("volume", 0.0),
                    })

            logger.info(f"Exported {len(events_sorted)} lifecycle events to {filepath}")

        except IOError as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise

    def get_management_actions(
        self,
        ticket: Optional[int] = None,
        action_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[ManagementAction]:
        """
        Get management actions from the database.

        Args:
            ticket: Filter by position ticket (optional)
            action_type: Filter by action type (optional)
            limit: Maximum number of actions to return (optional)

        Returns:
            List of ManagementAction records
        """
        actions = self._actions

        # Apply filters
        if ticket is not None:
            actions = [a for a in actions if a.ticket == ticket]

        if action_type is not None:
            actions = [a for a in actions if a.action_type == action_type]

        # Sort by timestamp descending
        actions = sorted(actions, key=lambda a: a.timestamp, reverse=True)

        # Apply limit
        if limit is not None:
            actions = actions[:limit]

        return actions

    def clear_history(self, ticket: Optional[int] = None) -> None:
        """
        Clear lifecycle history from memory and database.

        Args:
            ticket: Optional ticket to clear only that position's history.
                   If None, clears all history.
        """
        # Clear from memory
        if ticket is None:
            self._events.clear()
            self._actions.clear()
            logger.info("Cleared all lifecycle history from memory")
        else:
            self._events = [e for e in self._events if e.ticket != ticket]
            self._actions = [a for a in self._actions if a.ticket != ticket]
            logger.info(f"Cleared lifecycle history for position {ticket} from memory")

        # Clear from database
        if self._connection is not None:
            try:
                cursor = self._connection.cursor()

                if ticket is None:
                    cursor.execute("DELETE FROM lifecycle_events")
                    cursor.execute("DELETE FROM management_actions")
                    logger.info("Cleared all lifecycle history from database")
                else:
                    cursor.execute("DELETE FROM lifecycle_events WHERE ticket = ?", (ticket,))
                    cursor.execute("DELETE FROM management_actions WHERE ticket = ?", (ticket,))
                    logger.info(f"Cleared lifecycle history for position {ticket} from database")

                self._connection.commit()

            except sqlite3.Error as e:
                logger.error(f"Failed to clear history from database: {e}")

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        self.close()
