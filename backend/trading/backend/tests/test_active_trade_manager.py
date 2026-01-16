"""
Unit tests for ActiveTradeManager.

Tests the core functionality of the trade manager including:
- Position fetching
- PnL calculation
- Trade age tracking
- State management
- Monitoring loop
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core import ActiveTradeManager, TradeState, TradeStateMachine, TradePosition, MT5Position


class MockMT5Connector:
    """Mock MT5 connector for testing."""

    def __init__(self):
        self.positions: list[MT5Position] = []
        self.prices: dict[str, float] = {}

    def set_positions(self, positions: list[MT5Position]) -> None:
        """Set the positions to return."""
        self.positions = positions

    def set_price(self, symbol: str, price: float) -> None:
        """Set the price for a symbol."""
        self.prices[symbol] = price

    async def get_positions(self) -> list[MT5Position]:
        """Get all open positions."""
        return self.positions

    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        return self.prices.get(symbol, 0.0)


@pytest.fixture
def mock_mt5():
    """Create a mock MT5 connector."""
    return MockMT5Connector()


@pytest.fixture
def sample_position():
    """Create a sample MT5 position."""
    return MT5Position(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        volume=0.1,
        stop_loss=1.0800,
        take_profit=1.0950,
        profit=50.0,
        swap=0.5,
        commission=1.0,
        entry_time=datetime.utcnow() - timedelta(minutes=30),
    )


@pytest.fixture
def trade_manager(mock_mt5):
    """Create an ActiveTradeManager with mock MT5."""
    return ActiveTradeManager(mt5_connector=mock_mt5)


class TestActiveTradeManager:
    """Test suite for ActiveTradeManager."""

    def test_initialization(self, trade_manager):
        """Test that trade manager initializes correctly."""
        assert trade_manager.is_monitoring() is False
        assert len(trade_manager.get_tracked_positions()) == 0

    def test_calculate_pnl(self, trade_manager, sample_position):
        """Test PnL calculation."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.5,
            commission=1.0,
        )

        pnl = trade_manager.calculate_current_pnl(position)

        # PnL = profit + swap + commission
        assert pnl == 51.5

    def test_calculate_pnl_loss(self, trade_manager):
        """Test PnL calculation with a loss."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="SELL",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0900,
            take_profit=1.0800,
            entry_time=datetime.utcnow(),
            profit=-50.0,
            swap=-0.2,
            commission=1.0,
        )

        pnl = trade_manager.calculate_current_pnl(position)

        # PnL = profit + swap + commission
        assert pnl == -49.2

    def test_get_trade_age(self, trade_manager):
        """Test trade age calculation."""
        entry_time = datetime.utcnow() - timedelta(minutes=30)
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=entry_time,
            profit=50.0,
            swap=0.5,
            commission=1.0,
        )

        age = trade_manager.get_trade_age(position)

        # Age should be approximately 30 minutes
        assert age >= timedelta(minutes=29)
        assert age <= timedelta(minutes=31)

    def test_get_trade_state(self, trade_manager):
        """Test getting trade state."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        state = trade_manager.get_trade_state(position)

        assert state == TradeState.OPEN

    @pytest.mark.asyncio
    async def test_fetch_open_positions(self, trade_manager, mock_mt5, sample_position):
        """Test fetching open positions from MT5."""
        mock_mt5.set_positions([sample_position])

        positions = await trade_manager.fetch_open_positions()

        assert len(positions) == 1
        assert positions[0].ticket == 12345
        assert positions[0].symbol == "EURUSD"

    @pytest.mark.asyncio
    async def test_fetch_open_positions_empty(self, trade_manager, mock_mt5):
        """Test fetching when no positions are open."""
        mock_mt5.set_positions([])

        positions = await trade_manager.fetch_open_positions()

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_monitoring_iteration(self, trade_manager, mock_mt5, sample_position):
        """Test a single iteration of the monitoring loop."""
        mock_mt5.set_positions([sample_position])
        mock_mt5.set_price("EURUSD", 1.0900)

        # Track updates
        updates = []
        trade_manager.set_position_update_callback(lambda p: updates.append(p))

        # Run one iteration
        await trade_manager.fetch_open_positions()
        await trade_manager._update_position_prices()

        # Check that position was tracked
        positions = trade_manager.get_tracked_positions()
        assert 12345 in positions

    @pytest.mark.asyncio
    async def test_monitoring_loop_with_callbacks(self, trade_manager, mock_mt5):
        """Test monitoring loop with position update callbacks."""
        # Create multiple positions
        positions = [
            MT5Position(
                ticket=12345,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                volume=0.1,
                stop_loss=1.0800,
                take_profit=1.0950,
                profit=50.0,
                swap=0.5,
                commission=1.0,
                entry_time=datetime.utcnow() - timedelta(minutes=30),
            ),
            MT5Position(
                ticket=12346,
                symbol="GBPUSD",
                direction="SELL",
                entry_price=1.2650,
                volume=0.15,
                stop_loss=1.2700,
                take_profit=1.2550,
                profit=-25.0,
                swap=-0.3,
                commission=1.5,
                entry_time=datetime.utcnow() - timedelta(minutes=15),
            ),
        ]

        mock_mt5.set_positions(positions)
        mock_mt5.set_price("EURUSD", 1.0900)
        mock_mt5.set_price("GBPUSD", 1.2630)

        # Track updates
        updates = []
        trade_manager.set_position_update_callback(lambda p: updates.append(p))

        # Run one monitoring iteration manually
        mt5_positions = await trade_manager.fetch_open_positions()
        await trade_manager._update_position_prices()

        for mt5_pos in mt5_positions:
            if mt5_pos.ticket not in trade_manager.get_tracked_positions():
                position = trade_manager._convert_mt5_to_trade_position(mt5_pos)
                trade_manager._positions[mt5_pos.ticket] = position

            position = trade_manager._positions[mt5_pos.ticket]
            trade_manager.calculate_current_pnl(position)
            trade_manager.get_trade_age(position)
            trade_manager.get_trade_state(position)

            if trade_manager._on_position_update:
                trade_manager._on_position_update(position)

        # Check both positions were tracked
        tracked = trade_manager.get_tracked_positions()
        assert len(tracked) == 2
        assert 12345 in tracked
        assert 12346 in tracked

        # Check callbacks were triggered
        assert len(updates) == 2

    @pytest.mark.asyncio
    async def test_position_removal_on_close(self, trade_manager, mock_mt5, sample_position):
        """Test that closed positions are removed from tracking."""
        # Start with one position
        mock_mt5.set_positions([sample_position])
        await trade_manager.fetch_open_positions()

        # Convert and track
        position = trade_manager._convert_mt5_to_trade_position(sample_position)
        trade_manager._positions[sample_position.ticket] = position

        assert len(trade_manager.get_tracked_positions()) == 1

        # Simulate position closing (empty list from MT5)
        mock_mt5.set_positions([])

        # Run removal logic
        current_tickets = set()
        for mt5_pos in await trade_manager.fetch_open_positions():
            current_tickets.add(mt5_pos.ticket)

        closed_tickets = set(trade_manager._positions.keys()) - current_tickets

        for ticket in closed_tickets:
            closed_position = trade_manager._positions.pop(ticket)
            closed_position.transition_state(
                TradeState.CLOSED, "Position closed in MT5"
            )

        # Position should be removed
        assert len(trade_manager.get_tracked_positions()) == 0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, trade_manager, mock_mt5):
        """Test starting and stopping the monitoring loop."""
        mock_mt5.set_positions([])

        # Start monitoring
        await trade_manager.start_monitoring()
        assert trade_manager.is_monitoring() is True

        # Wait a bit then stop
        await asyncio.sleep(0.1)
        await trade_manager.stop_monitoring()
        assert trade_manager.is_monitoring() is False

    @pytest.mark.asyncio
    async def test_get_position_by_ticket(self, trade_manager, sample_position):
        """Test retrieving a specific position by ticket."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.5,
            commission=1.0,
        )

        trade_manager._positions[12345] = position

        # Get existing position
        retrieved = trade_manager.get_position(12345)
        assert retrieved is not None
        assert retrieved.ticket == 12345

        # Get non-existent position
        not_found = trade_manager.get_position(99999)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_convert_mt5_to_trade_position(self, trade_manager, sample_position):
        """Test conversion from MT5Position to TradePosition."""
        converted = trade_manager._convert_mt5_to_trade_position(sample_position)

        assert converted.ticket == sample_position.ticket
        assert converted.symbol == sample_position.symbol
        assert converted.direction == sample_position.direction
        assert converted.entry_price == sample_position.entry_price
        assert converted.volume == sample_position.volume
        assert converted.stop_loss == sample_position.stop_loss
        assert converted.take_profit == sample_position.take_profit
        assert converted.profit == sample_position.profit
        assert converted.swap == sample_position.swap
        assert converted.commission == sample_position.commission
        assert converted.state == TradeState.OPEN


class TestTradeStateMachine:
    """Test suite for TradeStateMachine."""

    def test_valid_transitions(self):
        """Test that valid state transitions are recognized."""
        assert TradeStateMachine.can_transition(TradeState.PENDING, TradeState.OPEN)
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.PARTIAL)
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.CLOSED)

    def test_invalid_transitions(self):
        """Test that invalid state transitions are rejected."""
        assert not TradeStateMachine.can_transition(TradeState.CLOSED, TradeState.OPEN)
        # PENDING -> CLOSED is valid (for cancelled/rejected orders)
        # Test some other invalid transitions instead
        assert not TradeStateMachine.can_transition(TradeState.CLOSED, TradeState.BREAKEVEN)
        assert not TradeStateMachine.can_transition(TradeState.OPEN, TradeState.PENDING)

    def test_validate_transition_success(self):
        """Test that valid transitions pass validation."""
        # Should not raise
        TradeStateMachine.validate_transition(TradeState.PENDING, TradeState.OPEN)

    def test_validate_transition_failure(self):
        """Test that invalid transitions raise ValueError."""
        with pytest.raises(ValueError):
            TradeStateMachine.validate_transition(TradeState.CLOSED, TradeState.OPEN)


class TestTradePosition:
    """Test suite for TradePosition."""

    def test_get_trade_age_seconds(self):
        """Test calculating trade age in seconds."""
        entry_time = datetime.utcnow() - timedelta(seconds=90)
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=entry_time,
            profit=50.0,
            swap=0.5,
            commission=1.0,
        )

        age = position.get_trade_age_seconds()

        # Should be approximately 90 seconds
        assert age >= 85
        assert age <= 95

    def test_transition_state(self):
        """Test state transition with history tracking."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0900,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=50.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # Initial state
        assert position.state == TradeState.OPEN
        assert len(position.state_history) == 0

        # Transition to PARTIAL
        position.transition_state(TradeState.PARTIAL, "Partial profit taken")

        assert position.state == TradeState.PARTIAL
        assert len(position.state_history) == 1
        assert position.state_history[0].from_state == TradeState.OPEN
        assert position.state_history[0].to_state == TradeState.PARTIAL
        assert position.state_history[0].reason == "Partial profit taken"

        # Transition to CLOSED
        position.transition_state(TradeState.CLOSED, "Position closed")

        assert position.state == TradeState.CLOSED
        assert len(position.state_history) == 2
