"""
Unit tests for TrailingStopManager.

Tests the trailing stop functionality including:
- Trail distance calculation
- LONG position trailing stop updates
- SHORT position trailing stop updates
- Minimum profit requirement
- Trail step validation
- Stop loss improvement checks
- Update history tracking
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from backend.core import (
    TrailingStopManager,
    TrailingStopConfig,
    TrailingStopUpdate,
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
def trailing_stop_manager(mock_mt5):
    """Create a TrailingStopManager with mock MT5."""
    return TrailingStopManager(mt5_connector=mock_mt5)


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
    """Create default trailing stop configuration."""
    return TrailingStopConfig(
        atr_multiplier=2.0,
        atr_period=14,
        min_profit_r=1.0,
        trail_step_atr_multiplier=0.5,
        enabled=True,
    )


class TestTrailingStopConfig:
    """Test suite for TrailingStopConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TrailingStopConfig()

        assert config.atr_multiplier == 2.0
        assert config.atr_period == 14
        assert config.min_profit_r == 1.0
        assert config.trail_step_atr_multiplier == 0.5
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TrailingStopConfig(
            atr_multiplier=3.0,
            atr_period=20,
            min_profit_r=1.5,
            trail_step_atr_multiplier=0.3,
            enabled=False,
        )

        assert config.atr_multiplier == 3.0
        assert config.atr_period == 20
        assert config.min_profit_r == 1.5
        assert config.trail_step_atr_multiplier == 0.3
        assert config.enabled is False


class TestCalculateTrailDistance:
    """Test suite for calculate_trail_distance method."""

    def test_calculate_trail_distance_default(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test trail distance calculation with default config."""
        distance = trailing_stop_manager.calculate_trail_distance(
            long_position, default_config
        )

        # With default ATR of 0.0010 and multiplier of 2.0
        assert distance == 0.0020

    def test_calculate_trail_distance_custom_multiplier(
        self, trailing_stop_manager, long_position
    ):
        """Test trail distance with custom ATR multiplier."""
        config = TrailingStopConfig(atr_multiplier=3.0)
        distance = trailing_stop_manager.calculate_trail_distance(
            long_position, config
        )

        # With default ATR of 0.0010 and multiplier of 3.0
        assert distance == 0.0030

    def test_calculate_trail_distance_short(
        self, trailing_stop_manager, short_position, default_config
    ):
        """Test trail distance calculation for SHORT position."""
        distance = trailing_stop_manager.calculate_trail_distance(
            short_position, default_config
        )

        # Distance should be same regardless of direction
        assert distance == 0.0020


class TestTrailingStopLongPositions:
    """Test suite for trailing stop on LONG (BUY) positions."""

    @pytest.mark.asyncio
    async def test_long_position_no_update_price_not_moved(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test no update when price hasn't moved enough."""
        # Price at entry, no movement
        long_position.current_price = 1.0850
        long_position.profit = 0.0

        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_long_position_no_update_not_enough_profit(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test no update when minimum profit requirement not met."""
        # Price moved up but not enough profit (less than 1R)
        long_position.current_price = 1.0870  # Moved 20 pips
        long_position.profit = 10.0  # Less than 1R (risk is 50 pips = $50)

        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_long_position_trailing_stop_updated(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test successful trailing stop update for LONG position."""
        # Price moved up significantly, above 1R profit
        long_position.current_price = 1.0900  # 50 pips up
        long_position.profit = 50.0  # Exactly 1R profit

        old_sl = long_position.stop_loss
        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        assert update is not None
        assert update.old_stop_loss == old_sl
        assert update.new_stop_loss > old_sl  # SL moved up (locks profit)
        assert long_position.stop_loss == update.new_stop_loss

    @pytest.mark.asyncio
    async def test_long_position_sl_never_moves_down(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test that SL never moves down on LONG positions."""
        # First update
        long_position.current_price = 1.0900
        long_position.profit = 50.0

        update1 = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        assert update1 is not None
        first_sl = update1.new_stop_loss

        # Price drops slightly but still profitable
        long_position.current_price = 1.0880
        long_position.profit = 30.0

        update2 = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        # SL should not move down
        assert update2 is None or long_position.stop_loss >= first_sl

    @pytest.mark.asyncio
    async def test_long_position_trail_step_validation(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test that trail step is respected (minimum movement)."""
        # First update
        long_position.current_price = 1.0900
        long_position.profit = 50.0

        update1 = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        assert update1 is not None
        first_sl = update1.new_stop_loss

        # Price moves up only slightly (less than trail step)
        long_position.current_price = 1.0905
        long_position.profit = 55.0

        update2 = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        # Should not update due to trail step
        assert update2 is None

    @pytest.mark.asyncio
    async def test_long_position_multiple_trailing_updates(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test multiple trailing stop updates as price continues up."""
        updates = []

        # Price moves to 1R
        long_position.current_price = 1.0900
        long_position.profit = 50.0
        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )
        if update:
            updates.append(update)

        # Price moves to 2R
        long_position.current_price = 1.0950
        long_position.profit = 100.0
        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )
        if update:
            updates.append(update)

        # Price moves to 3R
        long_position.current_price = 1.1000
        long_position.profit = 150.0
        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )
        if update:
            updates.append(update)

        # Should have multiple updates
        assert len(updates) >= 1

        # Each update should have higher SL
        for i in range(1, len(updates)):
            assert updates[i].new_stop_loss > updates[i - 1].new_stop_loss


class TestTrailingStopShortPositions:
    """Test suite for trailing stop on SHORT (SELL) positions."""

    @pytest.mark.asyncio
    async def test_short_position_no_update_price_not_moved(
        self, trailing_stop_manager, short_position, default_config
    ):
        """Test no update when price hasn't moved enough."""
        # Price at entry, no movement
        short_position.current_price = 1.0850
        short_position.profit = 0.0

        update = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_short_position_no_update_not_enough_profit(
        self, trailing_stop_manager, short_position, default_config
    ):
        """Test no update when minimum profit requirement not met."""
        # Price moved down but not enough profit
        short_position.current_price = 1.0830  # Moved 20 pips down
        short_position.profit = 10.0  # Less than 1R

        update = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_short_position_trailing_stop_updated(
        self, trailing_stop_manager, short_position, default_config
    ):
        """Test successful trailing stop update for SHORT position."""
        # Price moved down significantly, above 1R profit
        short_position.current_price = 1.0800  # 50 pips down
        short_position.profit = 50.0  # Exactly 1R profit

        old_sl = short_position.stop_loss
        update = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )

        assert update is not None
        assert update.old_stop_loss == old_sl
        assert update.new_stop_loss < old_sl  # SL moved down (locks profit)
        assert short_position.stop_loss == update.new_stop_loss

    @pytest.mark.asyncio
    async def test_short_position_sl_never_moves_up(
        self, trailing_stop_manager, short_position, default_config
    ):
        """Test that SL never moves up on SHORT positions."""
        # First update
        short_position.current_price = 1.0800
        short_position.profit = 50.0

        update1 = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )

        assert update1 is not None
        first_sl = update1.new_stop_loss

        # Price moves up slightly but still profitable
        short_position.current_price = 1.0820
        short_position.profit = 30.0

        update2 = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )

        # SL should not move up
        assert update2 is None or short_position.stop_loss <= first_sl

    @pytest.mark.asyncio
    async def test_short_position_multiple_trailing_updates(
        self, trailing_stop_manager, short_position, default_config
    ):
        """Test multiple trailing stop updates as price continues down."""
        updates = []

        # Price moves to 1R
        short_position.current_price = 1.0800
        short_position.profit = 50.0
        update = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )
        if update:
            updates.append(update)

        # Price moves to 2R
        short_position.current_price = 1.0750
        short_position.profit = 100.0
        update = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )
        if update:
            updates.append(update)

        # Price moves to 3R
        short_position.current_price = 1.0700
        short_position.profit = 150.0
        update = await trailing_stop_manager.update_trailing_stop(
            short_position, default_config
        )
        if update:
            updates.append(update)

        # Should have multiple updates
        assert len(updates) >= 1

        # Each update should have lower SL
        for i in range(1, len(updates)):
            assert updates[i].new_stop_loss < updates[i - 1].new_stop_loss


class TestTrailingStopConstraints:
    """Test suite for trailing stop constraints and edge cases."""

    @pytest.mark.asyncio
    async def test_trailing_stop_disabled(
        self, trailing_stop_manager, long_position
    ):
        """Test that trailing stop can be disabled."""
        config = TrailingStopConfig(enabled=False)

        long_position.current_price = 1.0900
        long_position.profit = 50.0

        update = await trailing_stop_manager.update_trailing_stop(
            long_position, config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_position_without_stop_loss(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test handling of position without stop loss."""
        long_position.stop_loss = None
        long_position.current_price = 1.0900
        long_position.profit = 50.0

        update = await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_custom_min_profit_requirement(
        self, trailing_stop_manager, long_position
    ):
        """Test custom minimum profit requirement."""
        # Require 1.5R before trailing starts
        config = TrailingStopConfig(min_profit_r=1.5)

        long_position.current_price = 1.0900
        long_position.profit = 50.0  # Only 1R, less than 1.5R requirement

        update = await trailing_stop_manager.update_trailing_stop(
            long_position, config
        )

        assert update is None

        # Now at 1.5R
        long_position.profit = 75.0
        long_position.current_price = 1.0925

        update = await trailing_stop_manager.update_trailing_stop(
            long_position, config
        )

        assert update is not None

    @pytest.mark.asyncio
    async def test_mt5_update_called(
        self, trailing_stop_manager, mock_mt5, long_position, default_config
    ):
        """Test that MT5 update is called when SL changes."""
        long_position.current_price = 1.0900
        long_position.profit = 50.0

        await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        # Verify MT5 update was called
        mock_mt5.update_stop_loss.assert_called_once()


class TestUpdateHistory:
    """Test suite for trailing stop update history tracking."""

    @pytest.mark.asyncio
    async def test_update_history_tracked(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test that updates are tracked in history."""
        long_position.current_price = 1.0900
        long_position.profit = 50.0

        await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        history = trailing_stop_manager.get_update_history()

        assert len(history) == 1
        assert history[0].ticket == long_position.ticket
        assert history[0].old_stop_loss == 1.0800
        assert history[0].new_stop_loss > 1.0800

    @pytest.mark.asyncio
    async def test_update_history_multiple_updates(
        self, trailing_stop_manager, long_position, default_config
    ):
        """Test history tracking with multiple updates."""
        # First update
        long_position.current_price = 1.0900
        long_position.profit = 50.0
        await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        # Second update
        long_position.current_price = 1.0950
        long_position.profit = 100.0
        await trailing_stop_manager.update_trailing_stop(
            long_position, default_config
        )

        history = trailing_stop_manager.get_update_history()

        assert len(history) == 2

    def test_update_history_filter_by_ticket(
        self, trailing_stop_manager, long_position, short_position
    ):
        """Test filtering update history by ticket."""
        # Manually add updates
        update1 = TrailingStopUpdate(
            ticket=12345,
            old_stop_loss=1.0800,
            new_stop_loss=1.0820,
            current_price=1.0900,
            trail_distance=0.0020,
            reason="Price moved up",
            timestamp=100,
        )

        update2 = TrailingStopUpdate(
            ticket=12346,
            old_stop_loss=1.0900,
            new_stop_loss=1.0880,
            current_price=1.0800,
            trail_distance=0.0020,
            reason="Price moved down",
            timestamp=200,
        )

        trailing_stop_manager._update_history.extend([update1, update2])

        # Get all history
        all_history = trailing_stop_manager.get_update_history()
        assert len(all_history) == 2

        # Filter by ticket
        filtered = trailing_stop_manager.get_update_history(ticket=12345)
        assert len(filtered) == 1
        assert filtered[0].ticket == 12345

    def test_clear_update_history(self, trailing_stop_manager):
        """Test clearing update history."""
        # Add some history
        update = TrailingStopUpdate(
            ticket=12345,
            old_stop_loss=1.0800,
            new_stop_loss=1.0820,
            current_price=1.0900,
            trail_distance=0.0020,
            reason="Test",
            timestamp=100,
        )

        trailing_stop_manager._update_history.append(update)
        assert len(trailing_stop_manager.get_update_history()) == 1

        # Clear history
        trailing_stop_manager.clear_update_history()
        assert len(trailing_stop_manager.get_update_history()) == 0


class TestTrailingStopUpdateDataclass:
    """Test suite for TrailingStopUpdate dataclass."""

    def test_trailing_stop_update_creation(self):
        """Test creating a TrailingStopUpdate record."""
        update = TrailingStopUpdate(
            ticket=12345,
            old_stop_loss=1.0800,
            new_stop_loss=1.0820,
            current_price=1.0900,
            trail_distance=0.0020,
            reason="Price moved up, SL raised to lock in profits",
            timestamp=100,
        )

        assert update.ticket == 12345
        assert update.old_stop_loss == 1.0800
        assert update.new_stop_loss == 1.0820
        assert update.current_price == 1.0900
        assert update.trail_distance == 0.0020
        assert update.timestamp == 100
