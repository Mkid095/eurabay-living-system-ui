"""
Unit tests for BreakevenManager.

Tests the breakeven functionality including:
- Breakeven price calculation
- LONG position breakeven triggers
- SHORT position breakeven triggers
- Profit trigger requirement (1.5R)
- Breakeven buffer (2 pips past entry)
- Breakeven lock (never move SL back)
- Breakeven cooldown (5 minutes after entry)
- Update history tracking
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.core import (
    BreakevenManager,
    BreakevenConfig,
    BreakevenUpdate,
    TradePosition,
    TradeState,
)


@pytest.fixture
def mock_mt5():
    """Create a mock MT5 connector."""
    mt5 = MagicMock()
    mt5.update_stop_loss = AsyncMock()
    return mt5


@pytest.fixture
def breakeven_manager(mock_mt5):
    """Create a BreakevenManager with mock MT5."""
    return BreakevenManager(mt5_connector=mock_mt5)


@pytest.fixture
def long_position():
    """Create a sample LONG (BUY) position."""
    return TradePosition(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        current_price=1.0850,
        volume=0.1,
        stop_loss=1.0800,
        take_profit=1.0950,
        entry_time=datetime.utcnow(),
        profit=0.0,
        swap=0.0,
        commission=0.0,
        state=TradeState.OPEN,
    )


@pytest.fixture
def short_position():
    """Create a sample SHORT (SELL) position."""
    return TradePosition(
        ticket=12346,
        symbol="EURUSD",
        direction="SELL",
        entry_price=1.0850,
        current_price=1.0850,
        volume=0.1,
        stop_loss=1.0900,
        take_profit=1.0750,
        entry_time=datetime.utcnow(),
        profit=0.0,
        swap=0.0,
        commission=0.0,
        state=TradeState.OPEN,
    )


@pytest.fixture
def default_config():
    """Create default breakeven configuration."""
    return BreakevenConfig(
        profit_trigger_r=1.5,
        buffer_pips=2.0,
        cooldown_seconds=300,
        enabled=True,
    )


class TestBreakevenConfig:
    """Test suite for BreakevenConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BreakevenConfig()

        assert config.profit_trigger_r == 1.5
        assert config.buffer_pips == 2.0
        assert config.cooldown_seconds == 300
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BreakevenConfig(
            profit_trigger_r=2.0,
            buffer_pips=3.0,
            cooldown_seconds=600,
            enabled=False,
        )

        assert config.profit_trigger_r == 2.0
        assert config.buffer_pips == 3.0
        assert config.cooldown_seconds == 600
        assert config.enabled is False


class TestCalculateBreakevenPrice:
    """Test suite for calculate_breakeven_price method."""

    def test_calculate_breakeven_price_long(
        self, breakeven_manager, long_position, default_config
    ):
        """Test breakeven price calculation for LONG position."""
        breakeven_price = breakeven_manager.calculate_breakeven_price(
            long_position, default_config
        )

        # For LONG: entry + buffer (2 pips = 0.0002)
        expected_price = 1.0850 + 0.0002
        assert breakeven_price == expected_price

    def test_calculate_breakeven_price_short(
        self, breakeven_manager, short_position, default_config
    ):
        """Test breakeven price calculation for SHORT position."""
        breakeven_price = breakeven_manager.calculate_breakeven_price(
            short_position, default_config
        )

        # For SHORT: entry - buffer (2 pips = 0.0002)
        expected_price = 1.0850 - 0.0002
        assert breakeven_price == expected_price

    def test_calculate_breakeven_price_custom_buffer(
        self, breakeven_manager, long_position
    ):
        """Test breakeven price with custom buffer."""
        config = BreakevenConfig(buffer_pips=5.0)
        breakeven_price = breakeven_manager.calculate_breakeven_price(
            long_position, config
        )

        # Entry + 5 pips (0.0005)
        expected_price = 1.0850 + 0.0005
        assert breakeven_price == expected_price


class TestBreakevenLongPositions:
    """Test suite for breakeven on LONG (BUY) positions."""

    @pytest.mark.asyncio
    async def test_long_position_no_update_not_enough_profit(
        self, breakeven_manager, long_position, default_config
    ):
        """Test no update when profit requirement not met."""
        # Price at 1R profit (less than 1.5R trigger)
        long_position.current_price = 1.0900
        long_position.profit = 50.0  # 1R, risk is 50 pips

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is None
        assert long_position.stop_loss == 1.0800  # Unchanged

    @pytest.mark.asyncio
    async def test_long_position_breakeven_triggered(
        self, breakeven_manager, long_position, default_config
    ):
        """Test successful breakeven trigger for LONG position."""
        # Set position age beyond cooldown period
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        # Price at 1.5R profit
        long_position.current_price = 1.0925
        long_position.profit = 75.0  # 1.5R profit

        old_sl = long_position.stop_loss
        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is not None
        assert update.old_stop_loss == old_sl
        assert update.new_stop_loss > old_sl  # SL moved up
        assert long_position.stop_loss == update.new_stop_loss
        # Breakeven should be entry + buffer
        assert abs(update.new_stop_loss - 1.0852) < 0.0001

    @pytest.mark.asyncio
    async def test_long_position_cooldown_active(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that cooldown prevents breakeven trigger."""
        # Position just entered (less than 5 minutes ago)
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=100)
        long_position.current_price = 1.0925
        long_position.profit = 75.0  # 1.5R profit

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_long_position_cooldown_expired(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that breakeven works after cooldown expires."""
        # Position entered more than 5 minutes ago
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0  # 1.5R profit

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is not None

    @pytest.mark.asyncio
    async def test_long_position_breakeven_lock(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that breakeven lock prevents SL from moving back."""
        # Position entered more than 5 minutes ago
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)

        # First trigger at 1.5R
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update1 = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update1 is not None
        assert breakeven_manager.is_position_locked(long_position.ticket)

        # Try to trigger again (should be skipped)
        update2 = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update2 is None  # Already locked

    @pytest.mark.asyncio
    async def test_long_position_custom_profit_trigger(
        self, breakeven_manager, long_position
    ):
        """Test custom profit trigger level."""
        # Require 2R before breakeven
        config = BreakevenConfig(profit_trigger_r=2.0)
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)

        # At 1.5R (should not trigger)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, config
        )

        assert update is None

        # At 2R (should trigger)
        long_position.current_price = 1.0950
        long_position.profit = 100.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, config
        )

        assert update is not None


class TestBreakevenShortPositions:
    """Test suite for breakeven on SHORT (SELL) positions."""

    @pytest.mark.asyncio
    async def test_short_position_no_update_not_enough_profit(
        self, breakeven_manager, short_position, default_config
    ):
        """Test no update when profit requirement not met."""
        # Price at 1R profit (less than 1.5R trigger)
        short_position.current_price = 1.0800
        short_position.profit = 50.0  # 1R

        update = await breakeven_manager.check_breakeven_trigger(
            short_position, default_config
        )

        assert update is None
        assert short_position.stop_loss == 1.0900  # Unchanged

    @pytest.mark.asyncio
    async def test_short_position_breakeven_triggered(
        self, breakeven_manager, short_position, default_config
    ):
        """Test successful breakeven trigger for SHORT position."""
        # Price at 1.5R profit
        short_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        short_position.current_price = 1.0775
        short_position.profit = 75.0  # 1.5R profit

        old_sl = short_position.stop_loss
        update = await breakeven_manager.check_breakeven_trigger(
            short_position, default_config
        )

        assert update is not None
        assert update.old_stop_loss == old_sl
        assert update.new_stop_loss < old_sl  # SL moved down
        assert short_position.stop_loss == update.new_stop_loss
        # Breakeven should be entry - buffer
        assert abs(update.new_stop_loss - 1.0848) < 0.0001

    @pytest.mark.asyncio
    async def test_short_position_cooldown_active(
        self, breakeven_manager, short_position, default_config
    ):
        """Test that cooldown prevents breakeven trigger."""
        # Position just entered
        short_position.current_price = 1.0775
        short_position.profit = 75.0  # 1.5R profit

        update = await breakeven_manager.check_breakeven_trigger(
            short_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_short_position_breakeven_lock(
        self, breakeven_manager, short_position, default_config
    ):
        """Test that breakeven lock prevents SL from moving back."""
        short_position.entry_time = datetime.utcnow() - timedelta(seconds=301)

        # First trigger at 1.5R
        short_position.current_price = 1.0775
        short_position.profit = 75.0

        update1 = await breakeven_manager.check_breakeven_trigger(
            short_position, default_config
        )

        assert update1 is not None
        assert breakeven_manager.is_position_locked(short_position.ticket)

        # Try to trigger again
        update2 = await breakeven_manager.check_breakeven_trigger(
            short_position, default_config
        )

        assert update2 is None  # Already locked


class TestBreakevenConstraints:
    """Test suite for breakeven constraints and edge cases."""

    @pytest.mark.asyncio
    async def test_breakeven_disabled(
        self, breakeven_manager, long_position
    ):
        """Test that breakeven can be disabled."""
        config = BreakevenConfig(enabled=False)
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_position_without_stop_loss(
        self, breakeven_manager, long_position, default_config
    ):
        """Test handling of position without stop loss."""
        long_position.stop_loss = None
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_position_with_zero_initial_risk(
        self, breakeven_manager, long_position, default_config
    ):
        """Test handling of position with zero initial risk."""
        # Same entry and SL means zero risk
        long_position.stop_loss = long_position.entry_price
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_breakeven_improvement_check(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that breakeven only improves SL position."""
        # Set SL above breakeven level (already better)
        long_position.stop_loss = 1.0860  # Above entry
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        # Should not update as current SL is already better
        assert update is None

    @pytest.mark.asyncio
    async def test_mt5_update_called(
        self, breakeven_manager, mock_mt5, long_position, default_config
    ):
        """Test that MT5 update is called when breakeven triggers."""
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        # Verify MT5 update was called
        mock_mt5.update_stop_loss.assert_called_once()


class TestBreakevenLock:
    """Test suite for breakeven lock functionality."""

    @pytest.mark.asyncio
    async def test_breakeven_lock_prevents_re_trigger(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that lock prevents multiple breakeven triggers."""
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)

        # First trigger
        long_position.current_price = 1.0925
        long_position.profit = 75.0
        update1 = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update1 is not None

        # Try to trigger again
        update2 = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update2 is None

    def test_is_position_locked(
        self, breakeven_manager, long_position, default_config
    ):
        """Test checking if position is locked."""
        # Not locked initially
        assert not breakeven_manager.is_position_locked(long_position.ticket)

        # Manually lock
        breakeven_manager._breakeven_locked.add(long_position.ticket)

        # Now locked
        assert breakeven_manager.is_position_locked(long_position.ticket)

    def test_unlock_position(
        self, breakeven_manager, long_position, default_config
    ):
        """Test unlocking a position."""
        # Lock position
        breakeven_manager._breakeven_locked.add(long_position.ticket)
        assert breakeven_manager.is_position_locked(long_position.ticket)

        # Unlock
        breakeven_manager.unlock_position(long_position.ticket)
        assert not breakeven_manager.is_position_locked(long_position.ticket)

    def test_get_locked_positions(
        self, breakeven_manager, long_position, short_position
    ):
        """Test getting all locked positions."""
        # Lock two positions
        breakeven_manager._breakeven_locked.add(long_position.ticket)
        breakeven_manager._breakeven_locked.add(short_position.ticket)

        locked = breakeven_manager.get_locked_positions()

        assert len(locked) == 2
        assert long_position.ticket in locked
        assert short_position.ticket in locked


class TestUpdateHistory:
    """Test suite for breakeven update history tracking."""

    @pytest.mark.asyncio
    async def test_update_history_tracked(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that updates are tracked in history."""
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        history = breakeven_manager.get_update_history()

        assert len(history) == 1
        assert history[0].ticket == long_position.ticket
        assert history[0].old_stop_loss == 1.0800
        assert history[0].new_stop_loss > 1.0800
        assert abs(history[0].profit_r - 1.5) < 0.01  # Allow for floating point precision

    def test_update_history_filter_by_ticket(
        self, breakeven_manager, long_position, short_position
    ):
        """Test filtering update history by ticket."""
        # Manually add updates
        update1 = BreakevenUpdate(
            ticket=12345,
            old_stop_loss=1.0800,
            new_stop_loss=1.0852,
            current_price=1.0925,
            profit_r=1.5,
            reason="Breakeven triggered",
            timestamp=100,
        )

        update2 = BreakevenUpdate(
            ticket=12346,
            old_stop_loss=1.0900,
            new_stop_loss=1.0848,
            current_price=1.0775,
            profit_r=1.5,
            reason="Breakeven triggered",
            timestamp=200,
        )

        breakeven_manager._update_history.extend([update1, update2])

        # Get all history
        all_history = breakeven_manager.get_update_history()
        assert len(all_history) == 2

        # Filter by ticket
        filtered = breakeven_manager.get_update_history(ticket=12345)
        assert len(filtered) == 1
        assert filtered[0].ticket == 12345

    def test_clear_update_history(self, breakeven_manager):
        """Test clearing update history."""
        # Add some history
        update = BreakevenUpdate(
            ticket=12345,
            old_stop_loss=1.0800,
            new_stop_loss=1.0852,
            current_price=1.0925,
            profit_r=1.5,
            reason="Test",
            timestamp=100,
        )

        breakeven_manager._update_history.append(update)
        assert len(breakeven_manager.get_update_history()) == 1

        # Clear history
        breakeven_manager.clear_update_history()
        assert len(breakeven_manager.get_update_history()) == 0


class TestBreakevenUpdateDataclass:
    """Test suite for BreakevenUpdate dataclass."""

    def test_breakeven_update_creation(self):
        """Test creating a BreakevenUpdate record."""
        update = BreakevenUpdate(
            ticket=12345,
            old_stop_loss=1.0800,
            new_stop_loss=1.0852,
            current_price=1.0925,
            profit_r=1.5,
            reason="Profit target reached, SL moved to breakeven",
            timestamp=100,
        )

        assert update.ticket == 12345
        assert update.old_stop_loss == 1.0800
        assert update.new_stop_loss == 1.0852
        assert update.current_price == 1.0925
        assert update.profit_r == 1.5
        assert update.timestamp == 100


class TestBreakevenEffectiveness:
    """Test suite for breakeven effectiveness metrics."""

    @pytest.mark.asyncio
    async def test_breakeven_protects_profit(
        self, breakeven_manager, long_position, default_config
    ):
        """Test that breakeven protects profit when price reverses."""
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=301)

        # Price reaches 1.5R, breakeven triggers
        long_position.current_price = 1.0925
        long_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            long_position, default_config
        )

        assert update is not None
        breakeven_sl = update.new_stop_loss

        # Price reverses to entry
        long_position.current_price = 1.0850
        long_position.profit = 20.0  # Still profitable due to breakeven

        # SL should be at breakeven level, preventing loss
        assert long_position.stop_loss == breakeven_sl
        assert long_position.stop_loss > long_position.entry_price

    @pytest.mark.asyncio
    async def test_breakeven_buffer_prevents_loss(
        self, breakeven_manager, short_position, default_config
    ):
        """Test that breakeven buffer prevents loss on SHORT positions."""
        short_position.entry_time = datetime.utcnow() - timedelta(seconds=301)

        # Price reaches 1.5R, breakeven triggers
        short_position.current_price = 1.0775
        short_position.profit = 75.0

        update = await breakeven_manager.check_breakeven_trigger(
            short_position, default_config
        )

        assert update is not None
        breakeven_sl = update.new_stop_loss

        # Breakeven SL should be below entry, preventing loss
        assert breakeven_sl < short_position.entry_price
        # With 2 pip buffer
        assert abs(breakeven_sl - (short_position.entry_price - 0.0002)) < 0.0001
