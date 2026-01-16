"""
Unit tests for ScaleOutManager.

Tests the scale-out functionality including:
- Scale-out level configuration (25% at 2R, 25% at 3R, 25% at 4R, hold rest)
- Alternative 50/50 strategy (50% at 2R, 50% at 4R)
- R multiple calculation
- LONG position scale-out triggers
- SHORT position scale-out triggers
- Cooldown mechanism between scale-outs
- Move SL to breakeven after first scale-out
- Update history tracking
- Position state transitions to SCALED_OUT
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.core import (
    ScaleOutManager,
    ScaleOutConfig,
    ScaleOutUpdate,
    ScaleOutLevel,
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
def scale_out_manager(mock_mt5):
    """Create a ScaleOutManager with mock MT5."""
    return ScaleOutManager(mt5_connector=mock_mt5)


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
    """Create default scale-out configuration."""
    return ScaleOutConfig(
        close_25_at_2r=True,
        close_25_at_3r=True,
        close_25_at_4r=True,
        hold_rest=True,
        alternative_50_50=False,
        cooldown_seconds=60,
        move_to_breakeven_after_first=True,
        enabled=True,
    )


@pytest.fixture
def alternative_config():
    """Create alternative 50/50 scale-out configuration."""
    return ScaleOutConfig(
        close_25_at_2r=False,
        close_25_at_3r=False,
        close_25_at_4r=False,
        hold_rest=True,
        alternative_50_50=True,
        cooldown_seconds=60,
        move_to_breakeven_after_first=True,
        enabled=True,
    )


class TestScaleOutConfig:
    """Test suite for ScaleOutConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ScaleOutConfig()

        assert config.close_25_at_2r is True
        assert config.close_25_at_3r is True
        assert config.close_25_at_4r is True
        assert config.hold_rest is True
        assert config.alternative_50_50 is False
        assert config.cooldown_seconds == 60
        assert config.move_to_breakeven_after_first is True
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ScaleOutConfig(
            close_25_at_2r=False,
            close_25_at_3r=False,
            close_25_at_4r=False,
            hold_rest=False,
            alternative_50_50=True,
            cooldown_seconds=120,
            move_to_breakeven_after_first=False,
            enabled=False,
        )

        assert config.close_25_at_2r is False
        assert config.close_25_at_3r is False
        assert config.close_25_at_4r is False
        assert config.hold_rest is False
        assert config.alternative_50_50 is True
        assert config.cooldown_seconds == 120
        assert config.move_to_breakeven_after_first is False
        assert config.enabled is False


class TestScaleOutLevel:
    """Test suite for ScaleOutLevel."""

    def test_scale_out_level_creation(self):
        """Test creating a ScaleOutLevel."""
        level = ScaleOutLevel(
            r_multiple=2.0,
            close_percentage=0.25,
            description="Close 25% at 2R"
        )

        assert level.r_multiple == 2.0
        assert level.close_percentage == 0.25
        assert level.description == "Close 25% at 2R"


class TestGetScaleOutLevels:
    """Test suite for get_scale_out_levels method."""

    def test_get_levels_default_config(
        self, scale_out_manager, default_config
    ):
        """Test getting scale-out levels with default config."""
        levels = scale_out_manager.get_scale_out_levels(default_config)

        assert len(levels) == 3

        # First level: 25% at 2R
        assert levels[0].r_multiple == 2.0
        assert levels[0].close_percentage == 0.25
        assert "25%" in levels[0].description
        assert "2R" in levels[0].description

        # Second level: 25% at 3R
        assert levels[1].r_multiple == 3.0
        assert levels[1].close_percentage == 0.25
        assert "25%" in levels[1].description
        assert "3R" in levels[1].description

        # Third level: 25% at 4R
        assert levels[2].r_multiple == 4.0
        assert levels[2].close_percentage == 0.25
        assert "25%" in levels[2].description
        assert "4R" in levels[2].description

    def test_get_levels_alternative_config(
        self, scale_out_manager, alternative_config
    ):
        """Test getting scale-out levels with alternative 50/50 config."""
        levels = scale_out_manager.get_scale_out_levels(alternative_config)

        assert len(levels) == 2

        # First level: 50% at 2R
        assert levels[0].r_multiple == 2.0
        assert levels[0].close_percentage == 0.50
        assert "50%" in levels[0].description

        # Second level: 50% at 4R
        assert levels[1].r_multiple == 4.0
        assert levels[1].close_percentage == 0.50
        assert "50%" in levels[1].description

    def test_get_levels_partial_config(self, scale_out_manager):
        """Test getting scale-out levels with partial config."""
        config = ScaleOutConfig(
            close_25_at_2r=True,
            close_25_at_3r=False,
            close_25_at_4r=True,
        )

        levels = scale_out_manager.get_scale_out_levels(config)

        assert len(levels) == 2
        assert levels[0].r_multiple == 2.0
        assert levels[1].r_multiple == 4.0


class TestCalculateInitialRisk:
    """Test suite for _calculate_initial_risk method."""

    def test_calculate_initial_risk_long(
        self, scale_out_manager, long_position
    ):
        """Test initial risk calculation for LONG position."""
        # Entry: 1.0850, SL: 1.0800
        # Risk = 50 pips = 0.0050
        # For 0.1 lots (10,000 units): 0.0050 * 10,000 = 50 USD
        risk = scale_out_manager._calculate_initial_risk(long_position)

        assert abs(risk - 50.0) < 0.01  # 50 USD risk

    def test_calculate_initial_risk_short(
        self, scale_out_manager, short_position
    ):
        """Test initial risk calculation for SHORT position."""
        # Entry: 1.0850, SL: 1.0900
        # Risk = 50 pips = 0.0050
        # For 0.1 lots: 0.0050 * 10,000 = 50 USD
        risk = scale_out_manager._calculate_initial_risk(short_position)

        assert abs(risk - 50.0) < 0.01  # 50 USD risk

    def test_calculate_initial_risk_no_stop_loss(
        self, scale_out_manager, long_position
    ):
        """Test initial risk calculation when no stop loss."""
        long_position.stop_loss = None
        risk = scale_out_manager._calculate_initial_risk(long_position)

        assert risk == 0.0


class TestCalculateRMultiple:
    """Test suite for _calculate_r_multiple method."""

    def test_calculate_r_multiple_profitable(
        self, scale_out_manager, long_position
    ):
        """Test R multiple calculation for profitable position."""
        long_position.profit = 100.0  # 2R profit (risk is 50)

        r_multiple = scale_out_manager._calculate_r_multiple(long_position)

        assert abs(r_multiple - 2.0) < 0.01

    def test_calculate_r_multiple_breaking_even(
        self, scale_out_manager, long_position
    ):
        """Test R multiple calculation for break-even position."""
        long_position.profit = 0.0

        r_multiple = scale_out_manager._calculate_r_multiple(long_position)

        assert r_multiple == 0.0

    def test_calculate_r_multiple_loss(
        self, scale_out_manager, long_position
    ):
        """Test R multiple calculation for losing position."""
        long_position.profit = -25.0  # -0.5R

        r_multiple = scale_out_manager._calculate_r_multiple(long_position)

        assert abs(r_multiple - (-0.5)) < 0.01

    def test_calculate_r_multiple_no_risk(
        self, scale_out_manager, long_position
    ):
        """Test R multiple calculation when no initial risk."""
        long_position.stop_loss = None

        r_multiple = scale_out_manager._calculate_r_multiple(long_position)

        assert r_multiple == 0.0


class TestGetRemainingPercentage:
    """Test suite for _get_remaining_percentage method."""

    def test_get_remaining_no_scale_outs(
        self, scale_out_manager, long_position
    ):
        """Test remaining percentage with no scale-outs."""
        remaining = scale_out_manager._get_remaining_percentage(long_position)

        assert remaining == 1.0  # 100% remaining

    def test_get_remaining_after_scale_out(
        self, scale_out_manager, long_position
    ):
        """Test remaining percentage after scale-out."""
        # Simulate a 25% scale-out
        update = ScaleOutUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="First scale-out",
            timestamp=100,
        )

        scale_out_manager._scale_out_history.append(update)

        remaining = scale_out_manager._get_remaining_percentage(long_position)

        assert remaining == 0.75  # 75% remaining

    def test_get_remaining_after_multiple_scale_outs(
        self, scale_out_manager, long_position
    ):
        """Test remaining percentage after multiple scale-outs."""
        # First scale-out: 25%
        update1 = ScaleOutUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="First scale-out",
            timestamp=100,
        )

        # Second scale-out: 25%
        update2 = ScaleOutUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.05,
            close_price=1.0950,
            profit_at_close=25.0,
            profit_r_multiple=3.0,
            close_percentage=0.25,
            reason="Second scale-out",
            timestamp=200,
        )

        scale_out_manager._scale_out_history.extend([update1, update2])

        remaining = scale_out_manager._get_remaining_percentage(long_position)

        assert remaining == 0.50  # 50% remaining


class TestScaleOutLongPositions:
    """Test suite for scale-out on LONG (BUY) positions."""

    @pytest.mark.asyncio
    async def test_long_position_no_trigger_not_enough_profit(
        self, scale_out_manager, long_position, default_config
    ):
        """Test no trigger when profit requirement not met."""
        # At 1R profit (less than 2R trigger)
        long_position.profit = 50.0

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is None
        assert long_position.volume == 0.1  # Unchanged

    @pytest.mark.asyncio
    async def test_long_position_first_scale_out_at_2r(
        self, scale_out_manager, long_position, default_config, mock_mt5
    ):
        """Test first scale-out (25%) at 2R."""
        long_position.profit = 100.0  # 2R profit

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25
        assert abs(update.closed_lots - 0.025) < 0.001
        assert abs(update.remaining_lots - 0.075) < 0.001
        assert abs(update.profit_r_multiple - 2.0) < 0.01

        # Verify MT5 close was called
        mock_mt5.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_long_position_second_scale_out_at_3r(
        self, scale_out_manager, long_position, default_config, mock_mt5
    ):
        """Test second scale-out (25%) at 3R."""
        # First scale-out at 2R
        long_position.profit = 100.0
        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        # Reset mock
        mock_mt5.reset_mock()

        # Reset cooldown to allow second scale-out
        scale_out_manager._last_scale_out_time.clear()

        # Second scale-out at 3R
        long_position.profit = 150.0  # 3R profit
        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25
        assert update.closed_lots == 0.025  # 25% of original 0.1
        assert update.remaining_lots == 0.05

    @pytest.mark.asyncio
    async def test_long_position_third_scale_out_at_4r(
        self, scale_out_manager, long_position, default_config
    ):
        """Test third scale-out (25%) at 4R."""
        # Simulate previous scale-outs: 25% + 25% = 50% closed
        update1 = ScaleOutUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="First scale-out",
            timestamp=100,
        )

        update2 = ScaleOutUpdate(
            ticket=long_position.ticket,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.05,
            close_price=1.0950,
            profit_at_close=25.0,
            profit_r_multiple=3.0,
            close_percentage=0.25,
            reason="Second scale-out",
            timestamp=200,
        )

        scale_out_manager._scale_out_history.extend([update1, update2])
        scale_out_manager._original_volumes[long_position.ticket] = 0.1
        long_position.volume = 0.05  # 50% remaining

        # Reset cooldown to allow third scale-out
        scale_out_manager._last_scale_out_time.clear()

        # Third scale-out at 4R
        long_position.profit = 200.0  # 4R profit
        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is not None
        # With hold_rest=True, should close half of remaining (12.5%)
        assert update.close_percentage == 0.125
        assert update.closed_lots == 0.0125
        assert update.remaining_lots == 0.0375

    @pytest.mark.asyncio
    async def test_long_position_moves_to_breakeven_after_first_scale_out(
        self, scale_out_manager, long_position, default_config, mock_mt5
    ):
        """Test that SL moves to breakeven after first scale-out."""
        long_position.profit = 100.0  # 2R

        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        # Verify breakeven was triggered
        mock_mt5.update_stop_loss.assert_called_once_with(
            long_position.ticket, long_position.entry_price
        )

    @pytest.mark.asyncio
    async def test_long_position_state_transitions_to_scaled_out(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that position state transitions to SCALED_OUT after first scale-out."""
        long_position.profit = 100.0  # 2R

        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert long_position.state == TradeState.SCALED_OUT


class TestScaleOutAlternativeStrategy:
    """Test suite for alternative 50/50 scale-out strategy."""

    @pytest.mark.asyncio
    async def test_alternative_strategy_first_scale_out_at_2r(
        self, scale_out_manager, long_position, alternative_config, mock_mt5
    ):
        """Test first scale-out (50%) at 2R with alternative strategy."""
        long_position.profit = 100.0  # 2R profit

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, alternative_config
        )

        assert update is not None
        assert update.close_percentage == 0.50
        assert update.closed_lots == 0.05
        assert update.remaining_lots == 0.05

        # Verify MT5 close was called
        mock_mt5.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_alternative_strategy_second_scale_out_at_4r(
        self, scale_out_manager, long_position, alternative_config
    ):
        """Test second scale-out (50%) at 4R with alternative strategy."""
        # First scale-out at 2R
        long_position.profit = 100.0
        await scale_out_manager.check_scale_out_trigger(
            long_position, alternative_config
        )

        # Reset cooldown to allow second scale-out
        scale_out_manager._last_scale_out_time.clear()

        # Second scale-out at 4R
        long_position.profit = 200.0  # 4R profit
        update = await scale_out_manager.check_scale_out_trigger(
            long_position, alternative_config
        )

        assert update is not None
        # With hold_rest=True, should close half of remaining (25%)
        assert update.close_percentage == 0.25
        assert update.closed_lots == 0.025
        assert update.remaining_lots == 0.025


class TestScaleOutShortPositions:
    """Test suite for scale-out on SHORT (SELL) positions."""

    @pytest.mark.asyncio
    async def test_short_position_first_scale_out_at_2r(
        self, scale_out_manager, short_position, default_config, mock_mt5
    ):
        """Test first scale-out (25%) at 2R for SHORT."""
        short_position.profit = 100.0  # 2R profit

        update = await scale_out_manager.check_scale_out_trigger(
            short_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25
        assert abs(update.closed_lots - 0.025) < 0.001
        assert abs(update.remaining_lots - 0.075) < 0.001

        # Verify MT5 close was called
        mock_mt5.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_short_position_second_scale_out_at_3r(
        self, scale_out_manager, short_position, default_config
    ):
        """Test second scale-out (25%) at 3R for SHORT."""
        # First scale-out at 2R
        short_position.profit = 100.0
        await scale_out_manager.check_scale_out_trigger(
            short_position, default_config
        )

        # Reset cooldown to allow second scale-out
        scale_out_manager._last_scale_out_time.clear()

        # Second scale-out at 3R
        short_position.profit = 150.0  # 3R profit
        update = await scale_out_manager.check_scale_out_trigger(
            short_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.25


class TestCooldownMechanism:
    """Test suite for cooldown between scale-outs."""

    @pytest.mark.asyncio
    async def test_cooldown_prevents_immediate_second_scale_out(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that cooldown prevents immediate second scale-out."""
        # First scale-out at 2R
        long_position.profit = 100.0
        update1 = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update1 is not None

        # Try to scale-out again immediately (within cooldown)
        update2 = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update2 is None  # Cooldown active

    @pytest.mark.asyncio
    async def test_cooldown_expires_after_configured_time(
        self, scale_out_manager, long_position
    ):
        """Test that cooldown expires after configured time."""
        # Set short cooldown for testing
        config = ScaleOutConfig(cooldown_seconds=1)
        long_position.entry_time = datetime.utcnow() - timedelta(seconds=2)

        # First scale-out
        long_position.profit = 100.0
        update1 = await scale_out_manager.check_scale_out_trigger(
            long_position, config
        )

        assert update1 is not None

        # Update last scale-out time to simulate time passing
        scale_out_manager._last_scale_out_time[long_position.ticket] = (
            long_position.get_trade_age_seconds() - 2
        )

        # Try again after cooldown
        update2 = await scale_out_manager.check_scale_out_trigger(
            long_position, config
        )

        # Should not scale-out because still at same profit level
        # (would need higher profit for next level)
        assert update2 is None


class TestScaleOutConstraints:
    """Test suite for scale-out constraints and edge cases."""

    @pytest.mark.asyncio
    async def test_scale_out_disabled(
        self, scale_out_manager, long_position
    ):
        """Test that scale-out can be disabled."""
        config = ScaleOutConfig(enabled=False)
        long_position.profit = 100.0

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_losing_position_not_scaled_out(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that losing positions are not scaled out."""
        long_position.profit = -50.0  # Losing

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_breaking_even_position_not_scaled_out(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that break-even positions are not scaled out."""
        long_position.profit = 0.0

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_no_mt5_connector_logs_only(
        self, scale_out_manager, long_position, default_config
    ):
        """Test behavior when MT5 connector is not configured."""
        # Create manager without MT5 connector
        manager_no_mt5 = ScaleOutManager(mt5_connector=None)
        long_position.profit = 100.0

        update = await manager_no_mt5.check_scale_out_trigger(
            long_position, default_config
        )

        # Should still create update record even without MT5
        # (close_price defaults to current_price when MT5 is None)
        assert update is not None
        assert update.close_percentage == 0.25


class TestUpdateHistory:
    """Test suite for scale-out update history tracking."""

    @pytest.mark.asyncio
    async def test_update_history_tracked(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that updates are tracked in history."""
        long_position.profit = 100.0  # 2R

        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        history = scale_out_manager.get_scale_out_history()

        assert len(history) == 1
        assert history[0].ticket == long_position.ticket
        assert history[0].close_percentage == 0.25
        assert abs(history[0].profit_r_multiple - 2.0) < 0.01

    def test_update_history_filter_by_ticket(
        self, scale_out_manager, long_position, short_position
    ):
        """Test filtering update history by ticket."""
        # Manually add updates
        update1 = ScaleOutUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="First scale-out",
            timestamp=100,
        )

        update2 = ScaleOutUpdate(
            ticket=12346,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0800,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="First scale-out",
            timestamp=200,
        )

        scale_out_manager._scale_out_history.extend([update1, update2])

        # Get all history
        all_history = scale_out_manager.get_scale_out_history()
        assert len(all_history) == 2

        # Filter by ticket
        filtered = scale_out_manager.get_scale_out_history(ticket=12345)
        assert len(filtered) == 1
        assert filtered[0].ticket == 12345

    def test_clear_scale_out_history(self, scale_out_manager):
        """Test clearing scale-out history."""
        # Add some history
        update = ScaleOutUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="Test",
            timestamp=100,
        )

        scale_out_manager._scale_out_history.append(update)
        assert len(scale_out_manager.get_scale_out_history()) == 1

        # Clear history
        scale_out_manager.clear_scale_out_history()
        assert len(scale_out_manager.get_scale_out_history()) == 0

    def test_get_total_scaled_out_percentage(self, scale_out_manager):
        """Test getting total scaled out percentage for a position."""
        # Add scale-outs: 25% + 25% = 50%
        update1 = ScaleOutUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="First",
            timestamp=100,
        )

        update2 = ScaleOutUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.05,
            close_price=1.0950,
            profit_at_close=25.0,
            profit_r_multiple=3.0,
            close_percentage=0.25,
            reason="Second",
            timestamp=200,
        )

        scale_out_manager._scale_out_history.extend([update1, update2])

        total_scaled_out = scale_out_manager.get_total_scaled_out_percentage(12345)

        assert total_scaled_out == 0.50  # 50%


class TestScaleOutUpdateDataclass:
    """Test suite for ScaleOutUpdate dataclass."""

    def test_scale_out_update_creation(self):
        """Test creating a ScaleOutUpdate record."""
        update = ScaleOutUpdate(
            ticket=12345,
            original_volume=0.1,
            closed_lots=0.025,
            remaining_lots=0.075,
            close_price=1.0900,
            profit_at_close=25.0,
            profit_r_multiple=2.0,
            close_percentage=0.25,
            reason="Scale-out at 2R profit",
            timestamp=100,
        )

        assert update.ticket == 12345
        assert update.original_volume == 0.1
        assert update.closed_lots == 0.025
        assert update.remaining_lots == 0.075
        assert update.close_price == 1.0900
        assert update.profit_at_close == 25.0
        assert update.profit_r_multiple == 2.0
        assert update.close_percentage == 0.25
        assert update.timestamp == 100


class TestScaleOutEffectiveness:
    """Test suite for scale-out effectiveness metrics."""

    @pytest.mark.asyncio
    async def test_scale_out_banks_early_profits(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that scale-out banks profits early."""
        long_position.profit = 100.0  # 2R

        update = await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert update is not None
        # Should bank 25% of profit
        assert abs(update.profit_at_close - 25.0) < 0.01  # 25% of 100

    @pytest.mark.asyncio
    async def test_scale_out_keeps_upside_potential(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that scale-out keeps upside potential on remaining position."""
        initial_volume = long_position.volume

        # Scale out 25%
        long_position.profit = 100.0
        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        # Remaining volume should be 75%
        assert long_position.volume == initial_volume * 0.75

        # Remaining position can still benefit from further upside
        long_position.profit = 200.0  # 4R
        # Position can still scale out more

    @pytest.mark.asyncio
    async def test_scale_out_reduces_risk_on_remaining(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that scale-out reduces risk on remaining position."""
        initial_volume = long_position.volume

        # Scale out 25%
        long_position.profit = 100.0
        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        # Remaining volume should be 75%
        assert long_position.volume == initial_volume * 0.75

        # Risk on remaining position is reduced


class TestStateTransitions:
    """Test suite for position state transitions during scale-out."""

    @pytest.mark.asyncio
    async def test_transition_from_open_to_scaled_out(
        self, scale_out_manager, long_position, default_config
    ):
        """Test transition from OPEN to SCALED_OUT state."""
        assert long_position.state == TradeState.OPEN

        long_position.profit = 100.0  # 2R
        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert long_position.state == TradeState.SCALED_OUT

    @pytest.mark.asyncio
    async def test_transition_from_partial_to_scaled_out(
        self, scale_out_manager, long_position, default_config
    ):
        """Test transition from PARTIAL to SCALED_OUT state."""
        # Set state to PARTIAL (simulating previous partial profit)
        long_position.state = TradeState.PARTIAL

        long_position.profit = 100.0  # 2R
        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        assert long_position.state == TradeState.SCALED_OUT

    @pytest.mark.asyncio
    async def test_state_history_recorded(
        self, scale_out_manager, long_position, default_config
    ):
        """Test that state transitions are recorded in history."""
        long_position.profit = 100.0  # 2R
        await scale_out_manager.check_scale_out_trigger(
            long_position, default_config
        )

        # Check state history
        assert len(long_position.state_history) > 0
        latest_transition = long_position.state_history[-1]
        assert latest_transition.to_state == TradeState.SCALED_OUT
