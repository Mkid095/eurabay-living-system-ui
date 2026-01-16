"""
Unit tests for HoldingTimeOptimizer.

Tests the holding time optimization functionality including:
- Configurable maximum holding times by market regime (trending, ranging, volatile)
- Trade age calculation
- Profitability checking
- Position close logic (50% at limit, 100% at 2x limit, 100% if losing)
- Holding time statistics tracking
- Update history tracking
- Position state transitions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.core import (
    HoldingTimeOptimizer,
    HoldingTimeConfig,
    HoldingTimeUpdate,
    MarketRegime,
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
    return mt5


@pytest.fixture
def holding_time_optimizer(mock_mt5):
    """Create a HoldingTimeOptimizer with mock MT5."""
    return HoldingTimeOptimizer(mt5_connector=mock_mt5)


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
    """Create default holding time configuration."""
    return HoldingTimeConfig(
        trending_max_hours=4.0,
        ranging_max_hours=2.0,
        volatile_max_hours=1.0,
        default_regime=MarketRegime.RANGING,
        close_percentage_at_limit=0.5,
        enabled=True,
    )


class TestMarketRegime:
    """Test suite for MarketRegime enum."""

    def test_market_regime_values(self):
        """Test market regime enum values."""
        assert MarketRegime.TRENDING.value == "trending"
        assert MarketRegime.RANGING.value == "ranging"
        assert MarketRegime.VOLATILE.value == "volatile"


class TestHoldingTimeConfig:
    """Test suite for HoldingTimeConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HoldingTimeConfig()

        assert config.trending_max_hours == 4.0
        assert config.ranging_max_hours == 2.0
        assert config.volatile_max_hours == 1.0
        assert config.default_regime == MarketRegime.RANGING
        assert config.close_percentage_at_limit == 0.5
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = HoldingTimeConfig(
            trending_max_hours=6.0,
            ranging_max_hours=3.0,
            volatile_max_hours=1.5,
            default_regime=MarketRegime.TRENDING,
            close_percentage_at_limit=0.75,
            enabled=False,
        )

        assert config.trending_max_hours == 6.0
        assert config.ranging_max_hours == 3.0
        assert config.volatile_max_hours == 1.5
        assert config.default_regime == MarketRegime.TRENDING
        assert config.close_percentage_at_limit == 0.75
        assert config.enabled is False


class TestGetMaxHoldingTimeSeconds:
    """Test suite for get_max_holding_time_seconds method."""

    def test_get_max_time_trending(self, holding_time_optimizer, default_config):
        """Test getting max holding time for trending regime."""
        max_seconds = holding_time_optimizer.get_max_holding_time_seconds(
            default_config, MarketRegime.TRENDING
        )

        assert max_seconds == 4 * 3600  # 4 hours in seconds

    def test_get_max_time_ranging(self, holding_time_optimizer, default_config):
        """Test getting max holding time for ranging regime."""
        max_seconds = holding_time_optimizer.get_max_holding_time_seconds(
            default_config, MarketRegime.RANGING
        )

        assert max_seconds == 2 * 3600  # 2 hours in seconds

    def test_get_max_time_volatile(self, holding_time_optimizer, default_config):
        """Test getting max holding time for volatile regime."""
        max_seconds = holding_time_optimizer.get_max_holding_time_seconds(
            default_config, MarketRegime.VOLATILE
        )

        assert max_seconds == 1 * 3600  # 1 hour in seconds

    def test_get_max_time_custom_config(self, holding_time_optimizer):
        """Test getting max holding time with custom config."""
        config = HoldingTimeConfig(
            trending_max_hours=6.0,
            ranging_max_hours=3.0,
            volatile_max_hours=1.5,
        )

        trending_seconds = holding_time_optimizer.get_max_holding_time_seconds(
            config, MarketRegime.TRENDING
        )
        ranging_seconds = holding_time_optimizer.get_max_holding_time_seconds(
            config, MarketRegime.RANGING
        )
        volatile_seconds = holding_time_optimizer.get_max_holding_time_seconds(
            config, MarketRegime.VOLATILE
        )

        assert trending_seconds == 6 * 3600
        assert ranging_seconds == 3 * 3600
        assert volatile_seconds == int(1.5 * 3600)


class TestIsPositionProfitable:
    """Test suite for _is_position_profitable method."""

    def test_profitable_position(self, holding_time_optimizer, long_position):
        """Test checking if position is profitable."""
        long_position.profit = 50.0
        long_position.swap = 1.0
        long_position.commission = -0.5

        is_profitable = holding_time_optimizer._is_position_profitable(long_position)

        assert is_profitable is True  # 50 + 1 - 0.5 = 50.5 > 0

    def test_losing_position(self, holding_time_optimizer, long_position):
        """Test checking if losing position is profitable."""
        long_position.profit = -50.0
        long_position.swap = 0.0
        long_position.commission = 0.0

        is_profitable = holding_time_optimizer._is_position_profitable(long_position)

        assert is_profitable is False

    def test_break_even_position(self, holding_time_optimizer, long_position):
        """Test checking if break-even position is profitable."""
        long_position.profit = 0.0
        long_position.swap = 0.0
        long_position.commission = 0.0

        is_profitable = holding_time_optimizer._is_position_profitable(long_position)

        assert is_profitable is False  # Exactly zero is not profitable

    def test_profit_after_swap_and_commission(self, holding_time_optimizer, long_position):
        """Test position with small profit but large swap/commission."""
        long_position.profit = 10.0
        long_position.swap = -5.0
        long_position.commission = -4.0

        is_profitable = holding_time_optimizer._is_position_profitable(long_position)

        assert is_profitable is True  # 10 - 5 - 4 = 1 > 0


class TestDetermineCloseAction:
    """Test suite for _determine_close_action method."""

    def test_losing_position_close_full(self, holding_time_optimizer):
        """Test that losing position closes fully."""
        close_percentage, reason = holding_time_optimizer._determine_close_action(
            trade_age_seconds=1000,
            max_allowed_seconds=7200,
            is_profitable=False
        )

        assert close_percentage == 1.0
        assert "Losing position" in reason

    def test_very_old_position_close_full(self, holding_time_optimizer):
        """Test that very old position (> 2x limit) closes fully."""
        close_percentage, reason = holding_time_optimizer._determine_close_action(
            trade_age_seconds=15000,
            max_allowed_seconds=7200,
            is_profitable=True
        )

        assert close_percentage == 1.0
        assert "very old" in reason.lower()

    def test_at_limit_close_partial(self, holding_time_optimizer):
        """Test that position at limit closes partially (50%)."""
        close_percentage, reason = holding_time_optimizer._determine_close_action(
            trade_age_seconds=7200,
            max_allowed_seconds=7200,
            is_profitable=True
        )

        assert close_percentage == 0.5
        assert "limit" in reason.lower()

    def test_before_limit_no_action(self, holding_time_optimizer):
        """Test that position before limit takes no action."""
        close_percentage, reason = holding_time_optimizer._determine_close_action(
            trade_age_seconds=5000,
            max_allowed_seconds=7200,
            is_profitable=True
        )

        assert close_percentage == 0.0
        assert reason == ""


class TestHoldingTimeLongPositions:
    """Test suite for holding time optimization on LONG (BUY) positions."""

    @pytest.mark.asyncio
    async def test_young_position_no_action(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that young position takes no action."""
        # Position is 1 hour old, limit is 2 hours
        long_position.entry_time = datetime.utcnow() - timedelta(hours=1)
        long_position.profit = 50.0

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is None
        assert long_position.volume == 0.1  # Unchanged

    @pytest.mark.asyncio
    async def test_at_limit_partial_close(
        self, holding_time_optimizer, long_position, default_config, mock_mt5
    ):
        """Test partial close (50%) when at holding time limit."""
        # Position is 2 hours old (at limit)
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 50.0  # Profitable

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.5
        assert update.closed_lots == 0.05
        assert update.remaining_lots == 0.05
        assert update.was_profitable is True

        # Verify MT5 close was called
        mock_mt5.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_very_old_full_close(
        self, holding_time_optimizer, long_position, default_config, mock_mt5
    ):
        """Test full close when position is very old (> 2x limit)."""
        # Position is 5 hours old (> 2x 2-hour limit)
        long_position.entry_time = datetime.utcnow() - timedelta(hours=5)
        long_position.profit = 50.0  # Profitable

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 1.0
        assert update.closed_lots == 0.1
        assert update.remaining_lots == 0.0

    @pytest.mark.asyncio
    async def test_losing_position_immediate_close(
        self, holding_time_optimizer, long_position, default_config, mock_mt5
    ):
        """Test immediate full close for losing position."""
        # Position is only 1 hour old but losing
        long_position.entry_time = datetime.utcnow() - timedelta(hours=1)
        long_position.profit = -50.0  # Losing

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 1.0
        assert update.was_profitable is False
        assert "Losing position" in update.reason


class TestHoldingTimeShortPositions:
    """Test suite for holding time optimization on SHORT (SELL) positions."""

    @pytest.mark.asyncio
    async def test_short_position_at_limit_partial_close(
        self, holding_time_optimizer, short_position, default_config, mock_mt5
    ):
        """Test partial close for SHORT position at limit."""
        # Position is 2 hours old (at limit)
        short_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        short_position.profit = 50.0  # Profitable

        update = await holding_time_optimizer.check_holding_time_limit(
            short_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.5
        assert update.closed_lots == 0.05

    @pytest.mark.asyncio
    async def test_short_position_losing_immediate_close(
        self, holding_time_optimizer, short_position, default_config
    ):
        """Test immediate close for losing SHORT position."""
        short_position.entry_time = datetime.utcnow() - timedelta(hours=1)
        short_position.profit = -30.0  # Losing

        update = await holding_time_optimizer.check_holding_time_limit(
            short_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 1.0
        assert update.was_profitable is False


class TestMarketRegimeSpecificBehavior:
    """Test suite for regime-specific holding time behavior."""

    @pytest.mark.asyncio
    async def test_trending_regime_allows_longer(
        self, holding_time_optimizer, long_position
    ):
        """Test that trending regime allows longer holding time."""
        config = HoldingTimeConfig(
            trending_max_hours=4.0,
            ranging_max_hours=2.0,
            volatile_max_hours=1.0,
        )

        # Position is 3 hours old
        long_position.entry_time = datetime.utcnow() - timedelta(hours=3)
        long_position.profit = 50.0

        # Should not close in trending regime
        update_trending = await holding_time_optimizer.check_holding_time_limit(
            long_position, config, regime=MarketRegime.TRENDING
        )
        assert update_trending is None

        # Should close in ranging regime
        update_ranging = await holding_time_optimizer.check_holding_time_limit(
            long_position, config, regime=MarketRegime.RANGING
        )
        assert update_ranging is not None

    @pytest.mark.asyncio
    async def test_volatile_regime_closes_sooner(
        self, holding_time_optimizer, long_position
    ):
        """Test that volatile regime closes positions sooner."""
        config = HoldingTimeConfig(
            trending_max_hours=4.0,
            ranging_max_hours=2.0,
            volatile_max_hours=1.0,
        )

        # Position is 1.5 hours old
        long_position.entry_time = datetime.utcnow() - timedelta(hours=1.5)
        long_position.profit = 50.0

        # Should not close in ranging regime
        update_ranging = await holding_time_optimizer.check_holding_time_limit(
            long_position, config, regime=MarketRegime.RANGING
        )
        assert update_ranging is None

        # Should close in volatile regime
        update_volatile = await holding_time_optimizer.check_holding_time_limit(
            long_position, config, regime=MarketRegime.VOLATILE
        )
        assert update_volatile is not None


class TestHoldingTimeConstraints:
    """Test suite for holding time constraints and edge cases."""

    @pytest.mark.asyncio
    async def test_holding_time_disabled(
        self, holding_time_optimizer, long_position
    ):
        """Test that holding time optimization can be disabled."""
        config = HoldingTimeConfig(enabled=False)
        long_position.entry_time = datetime.utcnow() - timedelta(hours=5)
        long_position.profit = 50.0

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, config
        )

        assert update is None

    @pytest.mark.asyncio
    async def test_no_mt5_connector_logs_only(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test behavior when MT5 connector is not configured."""
        # Create optimizer without MT5 connector
        optimizer_no_mt5 = HoldingTimeOptimizer(mt5_connector=None)
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 50.0

        update = await optimizer_no_mt5.check_holding_time_limit(
            long_position, default_config
        )

        # Should still create update record even without MT5
        assert update is not None
        assert update.close_percentage == 0.5

    @pytest.mark.asyncio
    async def test_default_regime_used_when_none_specified(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that default regime is used when none specified."""
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 50.0

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config, regime=None
        )

        assert update is not None
        assert update.regime == default_config.default_regime


class TestUpdateHistory:
    """Test suite for holding time update history tracking."""

    @pytest.mark.asyncio
    async def test_update_history_tracked(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that updates are tracked in history."""
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 50.0

        await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        history = holding_time_optimizer.get_close_history()

        assert len(history) == 1
        assert history[0].ticket == long_position.ticket
        assert history[0].close_percentage == 0.5

    def test_update_history_filter_by_ticket(
        self, holding_time_optimizer, long_position, short_position
    ):
        """Test filtering update history by ticket."""
        # Manually add updates
        update1 = HoldingTimeUpdate(
            ticket=12345,
            trade_age_seconds=7200,
            max_allowed_seconds=7200,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            was_profitable=True,
            close_percentage=0.5,
            regime=MarketRegime.RANGING,
            reason="At holding time limit",
            timestamp=7200,
        )

        update2 = HoldingTimeUpdate(
            ticket=12346,
            trade_age_seconds=7200,
            max_allowed_seconds=7200,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0800,
            profit_at_close=50.0,
            was_profitable=True,
            close_percentage=0.5,
            regime=MarketRegime.RANGING,
            reason="At holding time limit",
            timestamp=7200,
        )

        holding_time_optimizer._close_history.extend([update1, update2])

        # Get all history
        all_history = holding_time_optimizer.get_close_history()
        assert len(all_history) == 2

        # Filter by ticket
        filtered = holding_time_optimizer.get_close_history(ticket=12345)
        assert len(filtered) == 1
        assert filtered[0].ticket == 12345

    def test_clear_close_history(self, holding_time_optimizer):
        """Test clearing close history."""
        # Add some history
        update = HoldingTimeUpdate(
            ticket=12345,
            trade_age_seconds=7200,
            max_allowed_seconds=7200,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            was_profitable=True,
            close_percentage=0.5,
            regime=MarketRegime.RANGING,
            reason="Test",
            timestamp=7200,
        )

        holding_time_optimizer._close_history.append(update)
        assert len(holding_time_optimizer.get_close_history()) == 1

        # Clear history
        holding_time_optimizer.clear_close_history()
        assert len(holding_time_optimizer.get_close_history()) == 0


class TestStatistics:
    """Test suite for holding time statistics."""

    def test_empty_statistics(self, holding_time_optimizer):
        """Test statistics when no closes have occurred."""
        stats = holding_time_optimizer.get_statistics()

        assert stats["total_closes"] == 0
        assert stats["profitable_closes"] == 0
        assert stats["losing_closes"] == 0
        assert stats["average_holding_time"] == 0
        assert stats["by_regime"] == {}

    def test_statistics_with_closes(self, holding_time_optimizer):
        """Test statistics after some closes."""
        # Add some updates
        update1 = HoldingTimeUpdate(
            ticket=12345,
            trade_age_seconds=7200,
            max_allowed_seconds=7200,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            was_profitable=True,
            close_percentage=0.5,
            regime=MarketRegime.RANGING,
            reason="At limit",
            timestamp=7200,
        )

        update2 = HoldingTimeUpdate(
            ticket=12346,
            trade_age_seconds=3600,
            max_allowed_seconds=3600,
            closed_lots=0.1,
            remaining_lots=0.0,
            close_price=1.0800,
            profit_at_close=-30.0,
            was_profitable=False,
            close_percentage=1.0,
            regime=MarketRegime.VOLATILE,
            reason="Losing position",
            timestamp=3600,
        )

        holding_time_optimizer._close_history.extend([update1, update2])

        stats = holding_time_optimizer.get_statistics()

        assert stats["total_closes"] == 2
        assert stats["profitable_closes"] == 1
        assert stats["losing_closes"] == 1
        assert stats["average_holding_time"] == 5400  # (7200 + 3600) / 2
        assert len(stats["by_regime"]) == 2
        assert "ranging" in stats["by_regime"]
        assert "volatile" in stats["by_regime"]

    def test_statistics_by_regime(self, holding_time_optimizer):
        """Test statistics breakdown by regime."""
        # Add multiple closes for different regimes
        for i in range(3):
            update = HoldingTimeUpdate(
                ticket=12345 + i,
                trade_age_seconds=7200,
                max_allowed_seconds=7200,
                closed_lots=0.05,
                remaining_lots=0.05,
                close_price=1.0900,
                profit_at_close=50.0,
                was_profitable=True,
                close_percentage=0.5,
                regime=MarketRegime.RANGING,
                reason="At limit",
                timestamp=7200,
            )
            holding_time_optimizer._close_history.append(update)

        stats = holding_time_optimizer.get_statistics()

        assert "ranging" in stats["by_regime"]
        ranging_stats = stats["by_regime"]["ranging"]
        assert ranging_stats["count"] == 3
        assert ranging_stats["profitable"] == 3
        assert ranging_stats["losing"] == 0


class TestHoldingTimeUpdateDataclass:
    """Test suite for HoldingTimeUpdate dataclass."""

    def test_holding_time_update_creation(self):
        """Test creating a HoldingTimeUpdate record."""
        update = HoldingTimeUpdate(
            ticket=12345,
            trade_age_seconds=7200,
            max_allowed_seconds=7200,
            closed_lots=0.05,
            remaining_lots=0.05,
            close_price=1.0900,
            profit_at_close=50.0,
            was_profitable=True,
            close_percentage=0.5,
            regime=MarketRegime.RANGING,
            reason="At holding time limit",
            timestamp=7200,
        )

        assert update.ticket == 12345
        assert update.trade_age_seconds == 7200
        assert update.max_allowed_seconds == 7200
        assert update.closed_lots == 0.05
        assert update.remaining_lots == 0.05
        assert update.close_price == 1.0900
        assert update.profit_at_close == 50.0
        assert update.was_profitable is True
        assert update.close_percentage == 0.5
        assert update.regime == MarketRegime.RANGING
        assert "limit" in update.reason.lower()
        assert update.timestamp == 7200


class TestPositionStateTransitions:
    """Test suite for position state transitions."""

    @pytest.mark.asyncio
    async def test_partial_close_transitions_to_partial_state(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that partial close transitions position to PARTIAL state."""
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 50.0

        await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert long_position.state == TradeState.PARTIAL

    @pytest.mark.asyncio
    async def test_full_close_transitions_to_closed_state(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that full close transitions position to CLOSED state."""
        # Make position very old to trigger full close
        long_position.entry_time = datetime.utcnow() - timedelta(hours=5)
        long_position.profit = 50.0

        await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert long_position.state == TradeState.CLOSED


class TestHoldingTimeEffectiveness:
    """Test suite for holding time optimization effectiveness metrics."""

    @pytest.mark.asyncio
    async def test_holding_time_reduces_exposure(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that holding time optimization reduces market exposure."""
        initial_volume = long_position.volume

        # Position at limit, close 50%
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 50.0

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is not None
        # Volume should be reduced
        assert long_position.volume == initial_volume * 0.5

    @pytest.mark.asyncio
    async def test_holding_time_cuts_losses(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that holding time optimization cuts losing positions."""
        long_position.entry_time = datetime.utcnow() - timedelta(hours=1)
        long_position.profit = -50.0  # Losing

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 1.0  # Full close
        assert update.was_profitable is False
        # This prevents further losses

    @pytest.mark.asyncio
    async def test_holding_time_banks_profits(
        self, holding_time_optimizer, long_position, default_config
    ):
        """Test that holding time optimization banks profits at limit."""
        long_position.entry_time = datetime.utcnow() - timedelta(hours=2)
        long_position.profit = 100.0  # Profitable

        update = await holding_time_optimizer.check_holding_time_limit(
            long_position, default_config
        )

        assert update is not None
        assert update.close_percentage == 0.5
        assert update.was_profitable is True
        # Banks 50% of profit, keeps rest in market
