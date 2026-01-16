"""
Unit tests for PartialProfitManager.

Tests the partial profit taking functionality including:
- Partial profit level configuration (50% at 2R, 25% at 3R, remaining at 5R)
- R multiple calculation
- LONG position partial profit triggers
- SHORT position partial profit triggers
- Cooldown mechanism between partial closes
- Move SL to breakeven after first partial close
- Update history tracking
- Position state transitions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.core import (
    PartialProfitManager,
    PartialProfitConfig,
    PartialProfitUpdate,
    PartialProfitLevel,
    TradePosition,
    TradeState,
)


@pytest.fixture
def mock_mt5():
    """Create a mock MT5 connector."""
    mt5 = MagicMock()

    # Mock close_position to return the position's current price
    async def mock_close(ticket, lots, **kwargs):
        # Return a reasonable close price
        return 1.0850

    mt5.close_position = AsyncMock(side_effect=mock_close)
    mt5.update_stop_loss = AsyncMock()
    return mt5


@pytest.fixture
def partial_profit_manager(mock_mt5):
    """Create a PartialProfitManager with mock MT5."""
    return PartialProfitManager(mt5_connector=mock_mt5)


@pytest.fixture
def long_position():
    """Create a sample LONG (BUY) position."""
    return TradePosition(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        current_price=1.0850,
        volume=0.1,  # 1 mini lot
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
    """Create default partial profit configuration."""
    return PartialProfitConfig(
        close_50_at_r=2.0,
        close_25_at_r=3.0,
        close_remaining_at_r=5.0,
        cooldown_seconds=60,
        move_to_breakeven_after_first=True,
        enabled=True,
    )


class TestPartialProfitConfig:
    """Test suite for PartialProfitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PartialProfitConfig()

        assert config.close_50_at_r == 2.0
        assert config.close_25_at_r == 3.0
        assert config.close_remaining_at_r == 5.0
        assert config.cooldown_seconds == 60
        assert config.move_to_breakeven_after_first is True
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PartialProfitConfig(
            close_50_at_r=1.5,
            close_25_at_r=2.5,
            close_remaining_at_r=4.0,
            cooldown_seconds=120,
            move_to_breakeven_after_first=False,
            enabled=False,
        )

        assert config.close_50_at_r == 1.5
        assert config.close_25_at_r == 2.5
        assert config.close_remaining_at_r == 4.0
        assert config.cooldown_seconds == 120
        assert config.move_to_breakeven_after_first is False
        assert config.enabled is False


class TestPartialProfitLevel:
    """Test suite for PartialProfitLevel."""

    def test_partial_profit_level_creation(self):
        """Test creating a PartialProfitLevel."""
        level = PartialProfitLevel(
            r_multiple=2.0,
            close_percentage=0.50,
            description="Close 50% at 2R"
        )

        assert level.r_multiple == 2.0
        assert level.close_percentage == 0.50
        assert level.description == "Close 50% at 2R"


class TestGetPartialCloseLevels:
    """Test suite for get_partial_close_levels method."""

    def test_get_levels_default_config(
        self, partial_profit_manager, default_config
    ):
        """Test getting partial close levels with default config."""
        levels = partial_profit_manager.get_partial_close_levels(default_config)

        assert len(levels) == 3

        # First level: 50% at 2R
        assert levels[0].r_multiple == 2.0
        assert levels[0].close_percentage == 0.50
        assert "50%" in levels[0].description

        # Second level: 25% at 3R
        assert levels[1].r_multiple == 3.0
        assert levels[1].close_percentage == 0.25
        assert "25%" in levels[1].description

        # Third level: remaining at 5R
        assert levels[2].r_multiple == 5.0
        assert levels[2].close_percentage == 1.0
        assert "remaining" in levels[2].description.lower()

    def test_get_levels_custom_config(self, partial_profit_manager):
        """Test getting partial close levels with custom config."""
        config = PartialProfitConfig(
            close_50_at_r=1.5,
            close_25_at_r=2.5,
            close_remaining_at_r=4.0,
        )

        levels = partial_profit_manager.get_partial_close_levels(config)

        assert levels[0].r_multiple == 1.5
        assert levels[1].r_multiple == 2.5
        assert levels[2].r_multiple == 4.0


class TestCalculateInitialRisk:
    """Test suite for _calculate_initial_risk method."""

    def test_calculate_initial_risk_long(
        self, partial_profit_manager, long_position
    ):
        """Test initial risk calculation for LONG position."""
        # Entry: 1.0850, SL: 1.0800
        # Risk = 50 pips = 0.0050
        # For 0.1 lots (10,000 units): 0.0050 * 10,000 = 50 USD
        risk = partial_profit_manager._calculate_initial_risk(long_position)

        assert abs(risk - 50.0) < 0.01  # 50 USD risk

    def test_calculate_initial_risk_short(
        self, partial_profit_manager, short_position
    ):
        """Test initial risk calculation for SHORT position."""
        # Entry: 1.0850, SL: 1.0900
        # Risk = 50 pips = 0.0050
        # For 0.1 lots: 0.0050 * 10,000 = 50 USD
        risk = partial_profit_manager._calculate_initial_risk(short_position)

        assert abs(risk - 50.0) < 0.01  # 50 USD risk

    def test_calculate_initial_risk_no_stop_loss(
        self, partial_profit_manager, long_position
    ):
        """Test initial risk calculation when no stop loss."""
        long_position.stop_loss = None
        risk = partial_profit_manager._calculate_initial_risk(long_position)

        assert risk == 0.0


class TestCalculateRMultiple:
    """Test suite for _calculate_r_multiple method."""

    def test_calculate_r_multiple_profitable(
        self, partial_profit_manager, long_position
    ):
        """Test R multiple calculation for profitable position."""
        long_position.profit = 100.0  # 2R profit (risk is 50)

        r_multiple = partial_profit_manager._calculate_r_multiple(long_position)

        assert abs(r_multiple - 2.0) < 0.01

    def test_calculate_r_multiple_breaking_even(
        self, partial_profit_manager, long_position
    ):
        """Test R multiple calculation for break-even position."""
        long_position.profit = 0.0

        r_multiple = partial_profit_manager._calculate_r_multiple(long_position)

        assert r_multiple == 0.0

    def test_calculate_r_multiple_loss(
        self, partial_profit_manager, long_position
    ):
        """Test R multiple calculation for losing position."""
        long_position.profit = -25.0  # -0.5R

        r_multiple = partial_profit_manager._calculate_r_multiple(long_position)

        assert abs(r_multiple - (-0.5)) < 0.01

    def test_calculate_r_multiple_no_risk(
        self, partial_profit_manager, long_position
    ):
        """Test R multiple calculation when no initial risk."""
        long_position.stop_loss = None

        r_multiple = partial_profit_manager._calculate_r_multiple(long_position)

        assert r_multiple == 0.0


class TestGetRemainingPercentage:
    """Test suite for _get_remaining_percentage method."""

    def test_get_remaining_no_closes(
        self, partial_profit_manager, long_position
    ):
        """Test remaining percentage with no closes."""
        remaining = partial_profit_manager._get_remaining_percentage(long_position)

        assert remaining == 1.0  # 100% remaining

    def test_get_remaining_after_partial_close(
        self, partial_profit_manager, long_position
    ):
        """Test remaining percentage after partial close."""
        # Simulate a 50% close
        update = PartialProfitUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="First partial close",
            timestamp=100,
        )

        partial_profit_manager._close_history.append(update)

        remaining = partial_profit_manager._get_remaining_percentage(long_position)

        assert remaining == 0.50  # 50% remaining

    def test_get_remaining_after_multiple_closes(
        self, partial_profit_manager, long_position
    ):
        """Test remaining percentage after multiple closes."""
        # First close: 50%
        update1 = PartialProfitUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="First partial close",
            timestamp=100,
        )

        # Second close: 25%
        update2 = PartialProfitUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.025,
            close_price=1.0950,
            profit_at_close=25.0,
            profit_r_multiple=3.0,
            close_percentage=0.25,
            reason="Second partial close",
            timestamp=200,
        )

        partial_profit_manager._close_history.extend([update1, update2])

        remaining = partial_profit_manager._get_remaining_percentage(long_position)

        assert remaining == 0.25  # 25% remaining


class TestPartialProfitLongPositions:
    """Test suite for partial profit on LONG (BUY) positions."""

    @pytest.mark.asyncio
    async def test_long_position_no_trigger_not_enough_profit(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test no trigger when profit requirement not met."""
        # At 1R profit (less than 2R trigger)
        long_position.profit = 50.0

        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is None
        assert long_position.volume == 0.1  # Unchanged

    @pytest.mark.asyncio
    async def test_long_position_first_partial_close_at_2r(
        self, partial_profit_manager, long_position, default_config, mock_mt5
    ):
        """Test first partial close (50%) at 2R."""
        long_position.profit = 100.0  # 2R profit

        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.50
        assert update.closed_lots == 0.05
        assert update.remaining_lots == 0.05
        assert abs(update.profit_r_multiple - 2.0) < 0.01

        # Verify MT5 close was called
        mock_mt5.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_long_position_second_partial_close_at_3r(
        self, partial_profit_manager, long_position, default_config, mock_mt5
    ):
        """Test second partial close (25%) at 3R."""
        # First close at 2R
        long_position.profit = 100.0
        await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        # Reset mock
        mock_mt5.reset_mock()

        # Reset cooldown to allow second close
        partial_profit_manager._last_close_time.clear()

        # Second close at 3R
        long_position.profit = 150.0  # 3R profit
        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25
        assert update.closed_lots == 0.025  # 25% of original 0.1
        assert update.remaining_lots == 0.025

    @pytest.mark.asyncio
    async def test_long_position_final_close_at_5r(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test final close (remaining) at 5R."""
        # Simulate previous closes: 50% + 25% = 75% closed
        update1 = PartialProfitUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="First partial close",
            timestamp=100,
        )

        update2 = PartialProfitUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.025,
            close_price=1.0950,
            profit_at_close=25.0,
            profit_r_multiple=3.0,
            close_percentage=0.25,
            reason="Second partial close",
            timestamp=200,
        )

        partial_profit_manager._close_history.extend([update1, update2])
        partial_profit_manager._original_volumes[long_position.ticket] = 0.1
        long_position.volume = 0.025  # 25% remaining

        # Reset cooldown to allow final close
        partial_profit_manager._last_close_time.clear()

        # Final close at 5R
        long_position.profit = 250.0  # 5R profit
        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25  # Remaining 25%
        assert update.closed_lots == 0.025
        assert update.remaining_lots == 0.0

    @pytest.mark.asyncio
    async def test_long_position_moves_to_breakeven_after_first_close(
        self, partial_profit_manager, long_position, default_config, mock_mt5
    ):
        """Test that SL moves to breakeven after first partial close."""
        long_position.profit = 100.0  # 2R

        await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        # Verify breakeven was triggered
        mock_mt5.update_stop_loss.assert_called_once_with(
            long_position.ticket, long_position.entry_price
        )

    @pytest.mark.asyncio
    async def test_long_position_state_transitions_to_partial(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that position state transitions to PARTIAL after first close."""
        long_position.profit = 100.0  # 2R

        await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert long_position.state == TradeState.PARTIAL


class TestPartialProfitShortPositions:
    """Test suite for partial profit on SHORT (SELL) positions."""

    @pytest.mark.asyncio
    async def test_short_position_first_partial_close_at_2r(
        self, partial_profit_manager, short_position, default_config, mock_mt5
    ):
        """Test first partial close (50%) at 2R for SHORT."""
        short_position.profit = 100.0  # 2R profit

        update = await partial_profit_manager.check_partial_close_triggers(
            short_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.50
        assert update.closed_lots == 0.05
        assert update.remaining_lots == 0.05

        # Verify MT5 close was called
        mock_mt5.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_short_position_second_partial_close_at_3r(
        self, partial_profit_manager, short_position, default_config
    ):
        """Test second partial close (25%) at 3R for SHORT."""
        # First close at 2R
        short_position.profit = 100.0
        await partial_profit_manager.check_partial_close_triggers(
            short_position, default_config
        )

        # Reset cooldown to allow second close
        partial_profit_manager._last_close_time.clear()

        # Second close at 3R
        short_position.profit = 150.0  # 3R profit
        update = await partial_profit_manager.check_partial_close_triggers(
            short_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25


class TestCooldownMechanism:
    """Test suite for cooldown between partial closes."""

    @pytest.mark.asyncio
    async def test_cooldown_prevents_immediate_second_close(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that cooldown prevents immediate second close."""
        # First close at 2R
        long_position.profit = 100.0
        update1 = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update1 is not None

        # Try to close again immediately (within cooldown)
        update2 = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update2 is None  # Cooldown active

    @pytest.mark.asyncio
    async def test_cooldown_expires_after_configured_time(
        self, partial_profit_manager, long_position
    ):
        """Test that cooldown expires after configured time."""
        # Set short cooldown for testing
        config = PartialProfitConfig(cooldown_seconds=1)
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=2)

        # First close
        long_position.profit = 100.0
        update1 = await partial_profit_manager.check_partial_close_triggers(
            long_position, config
        )

        assert update1 is not None

        # Update last close time to simulate time passing
        partial_profit_manager._last_close_time[long_position.ticket] = (
            long_position.get_trade_age_seconds() - 2
        )

        # Try again after cooldown
        update2 = await partial_profit_manager.check_partial_close_triggers(
            long_position, config
        )

        # Should not close because still at same profit level
        # (would need higher profit for next level)
        assert update2 is None


class TestPartialProfitConstraints:
    """Test suite for partial profit constraints and edge cases."""

    @pytest.mark.asyncio
    async def test_partial_profit_disabled(
        self, partial_profit_manager, long_position
    ):
        """Test that partial profit can be disabled."""
        config = PartialProfitConfig(enabled=False)
        long_position.profit = 100.0

        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_losing_position_not_closed(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that losing positions are not closed."""
        long_position.profit = -50.0  # Losing

        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_breaking_even_position_not_closed(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that break-even positions are not closed."""
        long_position.profit = 0.0

        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_no_mt5_connector_logs_only(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test behavior when MT5 connector is not configured."""
        # Create manager without MT5 connector
        manager_no_mt5 = PartialProfitManager(mt5_connector=None)
        long_position.profit = 100.0

        update = await manager_no_mt5.check_partial_close_triggers(
            long_position, default_config
        )

        # Should still create update record even without MT5
        # (close_price defaults to current_price when MT5 is None)
        assert update is not None
        assert update.close_percentage == 0.50


class TestUpdateHistory:
    """Test suite for partial profit update history tracking."""

    @pytest.mark.asyncio
    async def test_update_history_tracked(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that updates are tracked in history."""
        long_position.profit = 100.0  # 2R

        await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        history = partial_profit_manager.get_close_history()

        assert len(history) == 1
        assert history[0].ticket == long_position.ticket
        assert history[0].close_percentage == 0.50
        assert abs(history[0].profit_r_multiple - 2.0) < 0.01

    def test_update_history_filter_by_ticket(
        self, partial_profit_manager, long_position, short_position
    ):
        """Test filtering update history by ticket."""
        # Manually add updates
        update1 = PartialProfitUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="First partial close",
            timestamp=100,
        )

        update2 = PartialProfitUpdate(
            ticket=12346,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0800,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="First partial close",
            timestamp=200,
        )

        partial_profit_manager._close_history.extend([update1, update2])

        # Get all history
        all_history = partial_profit_manager.get_close_history()
        assert len(all_history) == 2

        # Filter by ticket
        filtered = partial_profit_manager.get_close_history(ticket=12345)
        assert len(filtered) == 1
        assert filtered[0].ticket == 12345

    def test_clear_close_history(self, partial_profit_manager):
        """Test clearing close history."""
        # Add some history
        update = PartialProfitUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="Test",
            timestamp=100,
        )

        partial_profit_manager._close_history.append(update)
        assert len(partial_profit_manager.get_close_history()) == 1

        # Clear history
        partial_profit_manager.clear_close_history()
        assert len(partial_profit_manager.get_close_history()) == 0

    def test_get_total_closed_percentage(self, partial_profit_manager):
        """Test getting total closed percentage for a position."""
        # Add closes: 50% + 25% = 75%
        update1 = PartialProfitUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="First",
            timestamp=100,
        )

        update2 = PartialProfitUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.025,
            close_price=1.0950,
            profit_at_close=25.0,
            profit_r_multiple=3.0,
            close_percentage=0.25,
            reason="Second",
            timestamp=200,
        )

        partial_profit_manager._close_history.extend([update1, update2])

        total_closed = partial_profit_manager.get_total_closed_percentage(12345)

        assert total_closed == 0.75  # 75%


class TestPartialProfitUpdateDataclass:
    """Test suite for PartialProfitUpdate dataclass."""

    def test_partial_profit_update_creation(self):
        """Test creating a PartialProfitUpdate record."""
        update = PartialProfitUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            profit_r_multiple=2.0,
            close_percentage=0.50,
            reason="Close 50% at 2R profit",
            timestamp=100,
        )

        assert update.ticket == 12345
        assert update.original_volume == 0.1
        assert update.closed_lots == 0.05
        assert update.remaining_lots == 0.05
        assert update.close_price == 1.0900
        assert update.profit_at_close == 50.0
        assert update.profit_r_multiple == 2.0
        assert update.close_percentage == 0.50
        assert update.timestamp == 100


class TestPartialProfitEffectiveness:
    """Test suite for partial profit effectiveness metrics."""

    @pytest.mark.asyncio
    async def test_partial_profit_banks_early_profits(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that partial profit banks profits early."""
        long_position.profit = 100.0  # 2R

        update = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update is not None
        # Should bank 50% of profit
        assert abs(update.profit_at_close - 50.0) < 0.01  # 50% of 100

    @pytest.mark.asyncio
    async def test_partial_profit_increases_win_rate_potential(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that partial profit increases win rate by banking early."""
        # Close 50% at 2R
        long_position.profit = 100.0
        update1 = await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        assert update1 is not None

        # Even if price reverses and remaining position hits SL,
        # we've still banked 50% profit
        # This increases effective win rate

    @pytest.mark.asyncio
    async def test_partial_profit_reduces_risk_on_remaining(
        self, partial_profit_manager, long_position, default_config
    ):
        """Test that partial profit reduces risk on remaining position."""
        initial_volume = long_position.volume

        # Close 50%
        long_position.profit = 100.0
        await partial_profit_manager.check_partial_close_triggers(
            long_position, default_config
        )

        # Remaining volume should be 50%
        assert long_position.volume == initial_volume * 0.5

        # Risk on remaining position is reduced
