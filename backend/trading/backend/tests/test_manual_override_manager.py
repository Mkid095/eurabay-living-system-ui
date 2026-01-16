"""
Unit tests for ManualOverrideManager.

Tests the manual override functionality including:
- Manual position closing
- Trailing stop disable
- Breakeven disable
- Manual stop loss/take profit setting
- Management pause/resume
- Override history tracking
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.core import (
    ManualOverrideManager,
    TradeState,
    TradePosition,
    OverrideAction,
    OverrideResult,
    OverrideRecord,
    OverrideState,
)


@pytest.fixture
def sample_position():
    """Create a sample trade position."""
    return TradePosition(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        current_price=1.0880,
        volume=0.1,
        stop_loss=1.0800,
        take_profit=1.0950,
        entry_time=datetime.utcnow() - timedelta(minutes=30),
        profit=50.0,
        swap=0.5,
        commission=1.0,
        state=TradeState.OPEN,
    )


@pytest.fixture
def mock_mt5():
    """Create a mock MT5 connector."""
    mt5 = MagicMock()
    mt5.close_position = AsyncMock(return_value=True)
    mt5.modify_position = AsyncMock(return_value=True)
    return mt5


@pytest.fixture
def override_manager(mock_mt5):
    """Create a ManualOverrideManager with mock MT5."""
    return ManualOverrideManager(mt5_connector=mock_mt5)


class TestManualOverrideManager:
    """Test suite for ManualOverrideManager."""

    def test_initialization(self, override_manager):
        """Test that override manager initializes correctly."""
        assert len(override_manager.get_override_history()) == 0
        assert len(override_manager._override_states) == 0

    def test_get_override_state_creates_new_state(self, override_manager):
        """Test that getting override state creates a new state if not exists."""
        state = override_manager.get_override_state(12345)
        assert isinstance(state, OverrideState)
        assert state.management_paused is False
        assert state.trailing_stopped is False
        assert state.breakeven_stopped is False

    def test_get_override_state_returns_existing(self, override_manager):
        """Test that getting override state returns existing state."""
        state1 = override_manager.get_override_state(12345)
        state1.management_paused = True
        state2 = override_manager.get_override_state(12345)
        assert state2.management_paused is True

    @pytest.mark.asyncio
    async def test_close_position_full(self, override_manager, sample_position, mock_mt5):
        """Test closing a full position."""
        result = await override_manager.close_position(
            position=sample_position,
            user="trader1",
            reason="Taking profit",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.CLOSE_POSITION
        assert "Closed 0.1 lots" in result.message
        mock_mt5.close_position.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_close_position_partial(self, override_manager, sample_position, mock_mt5):
        """Test closing a partial position."""
        result = await override_manager.close_position(
            position=sample_position,
            user="trader1",
            reason="Banking partial profits",
            lots=0.05,
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.CLOSE_POSITION
        assert "Closed 0.05 lots" in result.message
        mock_mt5.close_position.assert_called_once_with(12345, 0.05)

    @pytest.mark.asyncio
    async def test_close_position_already_closed(self, override_manager, sample_position):
        """Test closing an already closed position."""
        sample_position.state = TradeState.CLOSED

        result = await override_manager.close_position(
            position=sample_position,
            user="trader1",
            reason="Test",
        )

        assert result.success is False
        assert "already closed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_close_position_invalid_lots(self, override_manager, sample_position):
        """Test closing with more lots than position has."""
        result = await override_manager.close_position(
            position=sample_position,
            user="trader1",
            reason="Test",
            lots=1.0,  # More than 0.1
        )

        assert result.success is False
        assert "Cannot close" in result.message

    @pytest.mark.asyncio
    async def test_disable_trailing_stop(self, override_manager, sample_position):
        """Test disabling trailing stop."""
        result = await override_manager.disable_trailing_stop(
            position=sample_position,
            user="trader1",
            reason="Volatility too high",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.DISABLE_TRAILING_STOP
        assert "Trailing stop disabled" in result.message

        # Check state was updated
        state = override_manager.get_override_state(sample_position.ticket)
        assert state.trailing_stopped is True

    @pytest.mark.asyncio
    async def test_disable_breakeven(self, override_manager, sample_position):
        """Test disabling breakeven."""
        result = await override_manager.disable_breakeven(
            position=sample_position,
            user="trader1",
            reason="Want to let position run",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.DISABLE_BREAKEVEN
        assert "Breakeven disabled" in result.message

        # Check state was updated
        state = override_manager.get_override_state(sample_position.ticket)
        assert state.breakeven_stopped is True

    @pytest.mark.asyncio
    async def test_set_manual_stop_loss(self, override_manager, sample_position, mock_mt5):
        """Test setting manual stop loss."""
        new_sl = 1.0830
        result = await override_manager.set_manual_stop_loss(
            position=sample_position,
            stop_loss=new_sl,
            user="trader1",
            reason="Support level",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.SET_MANUAL_STOP_LOSS
        assert f"{new_sl:.5f}" in result.message

        # Check position was updated
        assert sample_position.stop_loss == new_sl

        # Check state was updated
        state = override_manager.get_override_state(sample_position.ticket)
        assert state.manual_stop_loss == new_sl

        # Check MT5 was called
        mock_mt5.modify_position.assert_called_once_with(
            ticket=sample_position.ticket,
            stop_loss=new_sl,
        )

    @pytest.mark.asyncio
    async def test_set_manual_take_profit(self, override_manager, sample_position, mock_mt5):
        """Test setting manual take profit."""
        new_tp = 1.0980
        result = await override_manager.set_manual_take_profit(
            position=sample_position,
            take_profit=new_tp,
            user="trader1",
            reason="Resistance level",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.SET_MANUAL_TAKE_PROFIT
        assert f"{new_tp:.5f}" in result.message

        # Check position was updated
        assert sample_position.take_profit == new_tp

        # Check state was updated
        state = override_manager.get_override_state(sample_position.ticket)
        assert state.manual_take_profit == new_tp

        # Check MT5 was called
        mock_mt5.modify_position.assert_called_once_with(
            ticket=sample_position.ticket,
            take_profit=new_tp,
        )

    @pytest.mark.asyncio
    async def test_pause_management(self, override_manager, sample_position):
        """Test pausing management."""
        result = await override_manager.pause_management(
            position=sample_position,
            user="trader1",
            reason="News event",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.PAUSE_MANAGEMENT
        assert "paused" in result.message.lower()

        # Check state was updated
        state = override_manager.get_override_state(sample_position.ticket)
        assert state.management_paused is True

    @pytest.mark.asyncio
    async def test_resume_management(self, override_manager, sample_position):
        """Test resuming management."""
        # First pause
        override_manager.get_override_state(sample_position.ticket).management_paused = True

        # Then resume
        result = await override_manager.resume_management(
            position=sample_position,
            user="trader1",
            reason="News passed",
            confirmed=True,
        )

        assert result.success is True
        assert result.action == OverrideAction.RESUME_MANAGEMENT
        assert "resumed" in result.message.lower()

        # Check state was updated
        state = override_manager.get_override_state(sample_position.ticket)
        assert state.management_paused is False

    def test_is_management_paused(self, override_manager):
        """Test checking if management is paused."""
        ticket = 12345

        # Initially not paused
        assert override_manager.is_management_paused(ticket) is False

        # Pause it
        override_manager.get_override_state(ticket).management_paused = True
        assert override_manager.is_management_paused(ticket) is True

    def test_is_trailing_stopped(self, override_manager):
        """Test checking if trailing stop is disabled."""
        ticket = 12345

        # Initially not stopped
        assert override_manager.is_trailing_stopped(ticket) is False

        # Stop it
        override_manager.get_override_state(ticket).trailing_stopped = True
        assert override_manager.is_trailing_stopped(ticket) is True

    def test_is_breakeven_stopped(self, override_manager):
        """Test checking if breakeven is disabled."""
        ticket = 12345

        # Initially not stopped
        assert override_manager.is_breakeven_stopped(ticket) is False

        # Stop it
        override_manager.get_override_state(ticket).breakeven_stopped = True
        assert override_manager.is_breakeven_stopped(ticket) is True

    def test_override_history_tracking(self, override_manager, sample_position):
        """Test that override history is tracked."""
        # Add some override states
        state1 = override_manager.get_override_state(12345)
        state1.management_paused = True

        state2 = override_manager.get_override_state(67890)
        state2.trailing_stopped = True

        # States should be tracked
        assert len(override_manager._override_states) == 2

    def test_clear_override_state(self, override_manager):
        """Test clearing override state for a position."""
        ticket = 12345
        override_manager.get_override_state(ticket)
        assert ticket in override_manager._override_states

        override_manager.clear_override_state(ticket)
        assert ticket not in override_manager._override_states

    def test_clear_override_history(self, override_manager, sample_position):
        """Test clearing override history."""
        # Create some history
        record = OverrideRecord(
            ticket=sample_position.ticket,
            action=OverrideAction.CLOSE_POSITION,
            previous_value=0.1,
            new_value=0.0,
            timestamp=datetime.utcnow(),
            user="trader1",
            reason="Test",
            confirmed=False,
        )
        override_manager._record_override(record)

        assert len(override_manager.get_override_history()) == 1

        override_manager.clear_override_history()
        assert len(override_manager.get_override_history()) == 0

    def test_get_override_history_filtered(self, override_manager):
        """Test getting filtered override history."""
        # Create records for different tickets
        record1 = OverrideRecord(
            ticket=12345,
            action=OverrideAction.CLOSE_POSITION,
            previous_value=0.1,
            new_value=0.0,
            timestamp=datetime.utcnow(),
            user="trader1",
            reason="Test",
            confirmed=False,
        )
        record2 = OverrideRecord(
            ticket=67890,
            action=OverrideAction.PAUSE_MANAGEMENT,
            previous_value=None,
            new_value=None,
            timestamp=datetime.utcnow(),
            user="trader1",
            reason="Test",
            confirmed=False,
        )

        override_manager._record_override(record1)
        override_manager._record_override(record2)

        # Get all history
        all_history = override_manager.get_override_history()
        assert len(all_history) == 2

        # Get filtered history
        filtered = override_manager.get_override_history(ticket=12345)
        assert len(filtered) == 1
        assert filtered[0].ticket == 12345

    def test_set_override_callback(self, override_manager):
        """Test setting override callback."""
        callback_called = []

        def callback(record):
            callback_called.append(record)

        override_manager.set_override_callback(callback)

        # Create a record
        record = OverrideRecord(
            ticket=12345,
            action=OverrideAction.CLOSE_POSITION,
            previous_value=0.1,
            new_value=0.0,
            timestamp=datetime.utcnow(),
            user="trader1",
            reason="Test",
            confirmed=False,
        )
        override_manager._record_override(record)

        # Check callback was called
        assert len(callback_called) == 1
        assert callback_called[0] == record


@pytest.mark.asyncio
class TestManualOverrideManagerIntegration:
    """Integration tests for manual override functionality."""

    async def test_pause_prevents_automated_actions(self, override_manager, sample_position):
        """Test that pausing management prevents automated actions."""
        ticket = sample_position.ticket

        # Initially not paused
        assert override_manager.is_management_paused(ticket) is False
        assert override_manager.is_trailing_stopped(ticket) is False
        assert override_manager.is_breakeven_stopped(ticket) is False

        # Pause management
        await override_manager.pause_management(
            position=sample_position,
            user="trader1",
            reason="Testing pause",
        )

        # Check all pause states
        assert override_manager.is_management_paused(ticket) is True

    async def test_multiple_overrides_same_position(self, override_manager, sample_position):
        """Test applying multiple overrides to the same position."""
        ticket = sample_position.ticket

        # Apply multiple overrides
        await override_manager.disable_trailing_stop(
            position=sample_position,
            user="trader1",
            reason="Test 1",
        )

        await override_manager.disable_breakeven(
            position=sample_position,
            user="trader1",
            reason="Test 2",
        )

        await override_manager.pause_management(
            position=sample_position,
            user="trader1",
            reason="Test 3",
        )

        # Check all states
        state = override_manager.get_override_state(ticket)
        assert state.trailing_stopped is True
        assert state.breakeven_stopped is True
        assert state.management_paused is True

    async def test_resume_enables_automated_actions(self, override_manager, sample_position):
        """Test that resuming management enables automated actions."""
        ticket = sample_position.ticket

        # Pause first
        await override_manager.pause_management(
            position=sample_position,
            user="trader1",
            reason="Testing",
        )
        assert override_manager.is_management_paused(ticket) is True

        # Resume
        await override_manager.resume_management(
            position=sample_position,
            user="trader1",
            reason="Testing resume",
        )
        assert override_manager.is_management_paused(ticket) is False
