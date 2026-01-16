"""
Unit tests for ScaleInManager.

Tests the scale-in functionality for adding to winning positions.
"""

import pytest
from datetime import datetime, timedelta
from backend.core import (
    ScaleInManager,
    ScaleInConfig,
    ScaleInOperation,
    ScaleInPerformance,
    TradePosition,
    TradeState,
)


@pytest.fixture
def mock_mt5_connector():
    """Mock MT5 connector for testing."""
    class MockMT5Connector:
        def __init__(self):
            self.next_ticket = 10000

        async def place_order(
            self, symbol, order_type, volume, price, sl, tp, comment
        ):
            ticket = self.next_ticket
            self.next_ticket += 1
            return ticket

    return MockMT5Connector()


@pytest.fixture
def sample_position():
    """Create a sample trade position for testing."""
    return TradePosition(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1000,
        current_price=1.1050,
        volume=0.1,
        stop_loss=1.0950,
        take_profit=1.1150,
        entry_time=datetime.utcnow() - timedelta(hours=1),
        profit=50.0,  # ~1R profit
        swap=-0.5,
        commission=-0.3,
        state=TradeState.OPEN,
    )


@pytest.fixture
def sample_position_short():
    """Create a sample SHORT trade position for testing."""
    return TradePosition(
        ticket=12346,
        symbol="EURUSD",
        direction="SELL",
        entry_price=1.1050,
        current_price=1.1000,
        volume=0.1,
        stop_loss=1.1100,
        take_profit=1.0900,
        entry_time=datetime.utcnow() - timedelta(hours=1),
        profit=50.0,  # ~1R profit
        swap=-0.5,
        commission=-0.3,
        state=TradeState.OPEN,
    )


class TestScaleInConfig:
    """Tests for ScaleInConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ScaleInConfig()

        assert config.first_trigger_r == 1.0
        assert config.first_scale_percent == 50.0
        assert config.second_trigger_r == 2.0
        assert config.second_scale_percent == 25.0
        assert config.max_scale_factor == 200.0
        assert config.min_trend_strength == 0.6
        assert config.min_signal_quality == 0.7
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ScaleInConfig(
            first_trigger_r=1.5,
            first_scale_percent=30.0,
            second_trigger_r=3.0,
            second_scale_percent=20.0,
            max_scale_factor=150.0,
            min_trend_strength=0.7,
            min_signal_quality=0.8,
            enabled=False,
        )

        assert config.first_trigger_r == 1.5
        assert config.first_scale_percent == 30.0
        assert config.second_trigger_r == 3.0
        assert config.second_scale_percent == 20.0
        assert config.max_scale_factor == 150.0
        assert config.min_trend_strength == 0.7
        assert config.min_signal_quality == 0.8
        assert config.enabled is False


class TestScaleInManager:
    """Tests for ScaleInManager class."""

    def test_init(self, mock_mt5_connector):
        """Test ScaleInManager initialization."""
        manager = ScaleInManager(mock_mt5_connector)

        assert manager._mt5 == mock_mt5_connector
        assert manager._operation_history == []
        assert manager._performance_data == {}
        assert manager._scale_in_triggers == {}

    def test_init_without_mt5(self):
        """Test ScaleInManager initialization without MT5 connector."""
        manager = ScaleInManager()

        assert manager._mt5 is None
        assert manager._operation_history == []

    def test_calculate_initial_risk_long(self, sample_position):
        """Test initial risk calculation for LONG position."""
        manager = ScaleInManager()

        risk = manager._calculate_initial_risk(sample_position)

        # Expected: (1.1000 - 1.0950) * 0.1 * 100000 = 50
        expected_risk = abs(1.1000 - 1.0950) * 0.1 * 100000
        assert risk == pytest.approx(expected_risk, rel=1e-5)

    def test_calculate_initial_risk_short(self, sample_position_short):
        """Test initial risk calculation for SHORT position."""
        manager = ScaleInManager()

        risk = manager._calculate_initial_risk(sample_position_short)

        # Expected: (1.1100 - 1.1050) * 0.1 * 100000 = 50
        expected_risk = abs(1.1100 - 1.1050) * 0.1 * 100000
        assert risk == pytest.approx(expected_risk, rel=1e-5)

    def test_calculate_initial_risk_no_sl(self, sample_position):
        """Test initial risk calculation with no stop loss."""
        sample_position.stop_loss = None
        manager = ScaleInManager()

        risk = manager._calculate_initial_risk(sample_position)

        assert risk == 0.0

    def test_calculate_current_profit_r(self, sample_position):
        """Test current profit calculation in R multiples."""
        manager = ScaleInManager()

        profit_r = manager._calculate_current_profit_r(sample_position)

        # Expected: 50 / 50 = 1.0R
        assert profit_r == pytest.approx(1.0, rel=1e-5)

    def test_get_triggered_scales_empty(self, sample_position):
        """Test getting triggered scales for position with no history."""
        manager = ScaleInManager()

        triggers = manager._get_triggered_scales(sample_position.ticket)

        assert triggers == []

    def test_mark_trigger_executed(self, sample_position):
        """Test marking a trigger as executed."""
        manager = ScaleInManager()

        manager._mark_trigger_executed(sample_position.ticket, "first")

        triggers = manager._get_triggered_scales(sample_position.ticket)
        assert triggers == ["first"]

    def test_mark_multiple_triggers(self, sample_position):
        """Test marking multiple triggers as executed."""
        manager = ScaleInManager()

        manager._mark_trigger_executed(sample_position.ticket, "first")
        manager._mark_trigger_executed(sample_position.ticket, "second")

        triggers = manager._get_triggered_scales(sample_position.ticket)
        assert triggers == ["first", "second"]

    def test_clear_scale_in_tracking(self, sample_position):
        """Test clearing scale-in tracking for a position."""
        manager = ScaleInManager()

        manager._mark_trigger_executed(sample_position.ticket, "first")
        manager._clear_scale_in_tracking(sample_position.ticket)

        triggers = manager._get_triggered_scales(sample_position.ticket)
        assert triggers == []

    def test_check_max_scale_factor_within_limit(self, sample_position):
        """Test max scale factor check when within limit."""
        manager = ScaleInManager()
        config = ScaleInConfig(max_scale_factor=200.0)

        # Add 50% should be within 200% limit
        result = manager._check_max_scale_factor(
            sample_position, 0.05, config
        )

        assert result is True

    def test_check_max_scale_factor_exceeded(self, sample_position):
        """Test max scale factor check when exceeded."""
        manager = ScaleInManager()
        config = ScaleInConfig(max_scale_factor=150.0)

        # Add 100% would exceed 150% limit
        result = manager._check_max_scale_factor(
            sample_position, 0.1, config
        )

        assert result is False

    def test_check_trend_confirmation_long(self, sample_position):
        """Test trend confirmation for LONG position."""
        manager = ScaleInManager()
        config = ScaleInConfig()

        # Price above entry should pass trend confirmation
        result = manager._check_trend_confirmation(sample_position, config)

        assert result is True

    def test_check_trend_confirmation_long_failed(self, sample_position):
        """Test trend confirmation failure for LONG position."""
        sample_position.current_price = 1.0990  # Below entry
        manager = ScaleInManager()
        config = ScaleInConfig()

        result = manager._check_trend_confirmation(sample_position, config)

        assert result is False

    def test_check_trend_confirmation_short(self, sample_position_short):
        """Test trend confirmation for SHORT position."""
        manager = ScaleInManager()
        config = ScaleInConfig()

        # Price below entry should pass trend confirmation
        result = manager._check_trend_confirmation(sample_position_short, config)

        assert result is True

    def test_check_trend_confirmation_short_failed(self, sample_position_short):
        """Test trend confirmation failure for SHORT position."""
        sample_position_short.current_price = 1.1060  # Above entry
        manager = ScaleInManager()
        config = ScaleInConfig()

        result = manager._check_trend_confirmation(sample_position_short, config)

        assert result is False

    def test_check_signal_quality(self, sample_position):
        """Test signal quality check."""
        manager = ScaleInManager()
        config = ScaleInConfig()

        result = manager._check_signal_quality(sample_position, config)

        # Default signal quality is 0.8, which is >= 0.7
        assert result is True

    def test_calculate_weighted_average_sl(self, sample_position):
        """Test weighted average SL calculation."""
        manager = ScaleInManager()

        new_sl = manager._calculate_weighted_average_sl(sample_position, 0.05)

        # Expected: (0.1 * 1.0950 + 0.05 * 1.0950) / 0.15 = 1.0950
        # Since both SLs are the same, result should be the same
        assert new_sl == pytest.approx(1.0950, rel=1e-5)

    def test_calculate_weighted_average_sl_no_sl(self, sample_position):
        """Test weighted average SL calculation with no SL."""
        sample_position.stop_loss = None
        manager = ScaleInManager()

        new_sl = manager._calculate_weighted_average_sl(sample_position, 0.05)

        assert new_sl is None

    @pytest.mark.asyncio
    async def test_check_scale_in_trigger_first(self, sample_position, mock_mt5_connector):
        """Test first scale-in trigger."""
        manager = ScaleInManager(mock_mt5_connector)
        config = ScaleInConfig()

        operation = await manager.check_scale_in_trigger(sample_position, config)

        assert operation is not None
        assert operation.ticket == sample_position.ticket
        assert operation.added_volume == pytest.approx(0.05, rel=1e-5)  # 50% of 0.1
        assert operation.scale_percent == pytest.approx(0.5, rel=1e-5)
        assert operation.new_ticket == 10000

    @pytest.mark.asyncio
    async def test_check_scale_in_trigger_disabled(self, sample_position):
        """Test scale-in trigger when disabled."""
        manager = ScaleInManager()
        config = ScaleInConfig(enabled=False)

        operation = await manager.check_scale_in_trigger(sample_position, config)

        assert operation is None

    @pytest.mark.asyncio
    async def test_check_scale_in_trigger_not_profitable(self, sample_position):
        """Test scale-in trigger when not profitable."""
        sample_position.profit = -25.0
        manager = ScaleInManager()
        config = ScaleInConfig()

        operation = await manager.check_scale_in_trigger(sample_position, config)

        assert operation is None

    @pytest.mark.asyncio
    async def test_check_scale_in_trigger_already_executed(
        self, sample_position, mock_mt5_connector
    ):
        """Test scale-in trigger when already executed."""
        manager = ScaleInManager(mock_mt5_connector)
        config = ScaleInConfig()

        # Execute first trigger
        await manager.check_scale_in_trigger(sample_position, config)

        # Try again - should not trigger again
        operation = await manager.check_scale_in_trigger(sample_position, config)

        assert operation is None

    @pytest.mark.asyncio
    async def test_check_scale_in_trigger_second(
        self, sample_position, mock_mt5_connector
    ):
        """Test second scale-in trigger."""
        manager = ScaleInManager(mock_mt5_connector)
        config = ScaleInConfig()

        # Set profit to 2R
        sample_position.profit = 100.0

        # Execute first trigger
        first_operation = await manager.check_scale_in_trigger(sample_position, config)
        assert first_operation is not None

        # Execute second trigger
        second_operation = await manager.check_scale_in_trigger(sample_position, config)
        assert second_operation is not None
        assert second_operation.scale_percent == pytest.approx(0.25, rel=1e-5)  # 25%
        assert second_operation.new_ticket == 10001

    @pytest.mark.asyncio
    async def test_check_scale_in_trigger_max_factor_exceeded(
        self, sample_position, mock_mt5_connector
    ):
        """Test scale-in trigger when max factor is exceeded."""
        manager = ScaleInManager(mock_mt5_connector)
        config = ScaleInConfig(max_scale_factor=120.0)

        # First scale-in (50%) should exceed 120% limit
        # Actually 150% > 120%, so it should fail
        operation = await manager.check_scale_in_trigger(sample_position, config)

        assert operation is None

    def test_get_operation_history_all(self, sample_position):
        """Test getting all operation history."""
        manager = ScaleInManager()

        operation = ScaleInOperation(
            ticket=sample_position.ticket,
            new_ticket=10000,
            original_volume=0.1,
            added_volume=0.05,
            total_volume=0.15,
            scale_percent=0.5,
            trigger_price=1.1050,
            fill_price=1.1050,
            new_stop_loss=1.0950,
            old_stop_loss=1.0950,
            reason="Test",
            timestamp=100.0,
        )
        manager._operation_history.append(operation)

        history = manager.get_operation_history()

        assert len(history) == 1
        assert history[0].ticket == sample_position.ticket

    def test_get_operation_history_filtered(self, sample_position):
        """Test getting operation history filtered by ticket."""
        manager = ScaleInManager()

        operation1 = ScaleInOperation(
            ticket=12345,
            new_ticket=10000,
            original_volume=0.1,
            added_volume=0.05,
            total_volume=0.15,
            scale_percent=0.5,
            trigger_price=1.1050,
            fill_price=1.1050,
            new_stop_loss=1.0950,
            old_stop_loss=1.0950,
            reason="Test",
            timestamp=100.0,
        )
        operation2 = ScaleInOperation(
            ticket=12346,
            new_ticket=10001,
            original_volume=0.1,
            added_volume=0.05,
            total_volume=0.15,
            scale_percent=0.5,
            trigger_price=1.1050,
            fill_price=1.1050,
            new_stop_loss=1.0950,
            old_stop_loss=1.0950,
            reason="Test",
            timestamp=100.0,
        )
        manager._operation_history.extend([operation1, operation2])

        history = manager.get_operation_history(ticket=12345)

        assert len(history) == 1
        assert history[0].ticket == 12345

    def test_record_performance(self, sample_position):
        """Test recording performance data."""
        manager = ScaleInManager()

        manager.record_performance(
            ticket=sample_position.ticket,
            final_profit_r=2.5,
            scale_in_profit_r=0.5,
            would_have_profit_r=2.0,
        )

        performance = manager.get_performance_data(sample_position.ticket)

        assert performance is not None
        assert performance.ticket == sample_position.ticket
        assert performance.final_profit_r == 2.5
        assert performance.scale_in_profit_r == 0.5
        assert performance.would_have_profit_r == 2.0
        assert performance.improvement_r == 0.5

    def test_get_performance_data_not_found(self, sample_position):
        """Test getting performance data for non-existent position."""
        manager = ScaleInManager()

        performance = manager.get_performance_data(sample_position.ticket)

        assert performance is None

    def test_get_all_performance_data(self, sample_position):
        """Test getting all performance data."""
        manager = ScaleInManager()

        manager.record_performance(12345, 2.5, 0.5, 2.0)
        manager.record_performance(12346, 1.8, 0.3, 1.5)

        all_performance = manager.get_all_performance_data()

        assert len(all_performance) == 2

    def test_clear_operation_history(self, sample_position):
        """Test clearing operation history."""
        manager = ScaleInManager()

        operation = ScaleInOperation(
            ticket=sample_position.ticket,
            new_ticket=10000,
            original_volume=0.1,
            added_volume=0.05,
            total_volume=0.15,
            scale_percent=0.5,
            trigger_price=1.1050,
            fill_price=1.1050,
            new_stop_loss=1.0950,
            old_stop_loss=1.0950,
            reason="Test",
            timestamp=100.0,
        )
        manager._operation_history.append(operation)

        manager.clear_operation_history()

        assert manager._operation_history == []

    def test_clear_performance_data_single(self, sample_position):
        """Test clearing performance data for single position."""
        manager = ScaleInManager()

        manager.record_performance(sample_position.ticket, 2.5, 0.5, 2.0)
        manager.clear_performance_data(ticket=sample_position.ticket)

        performance = manager.get_performance_data(sample_position.ticket)

        assert performance is None

    def test_clear_performance_data_all(self, sample_position):
        """Test clearing all performance data."""
        manager = ScaleInManager()

        manager.record_performance(12345, 2.5, 0.5, 2.0)
        manager.record_performance(12346, 1.8, 0.3, 1.5)
        manager.clear_performance_data()

        assert manager._performance_data == {}


class TestScaleInOperation:
    """Tests for ScaleInOperation dataclass."""

    def test_scale_in_operation_creation(self):
        """Test creating a ScaleInOperation."""
        operation = ScaleInOperation(
            ticket=12345,
            new_ticket=10000,
            original_volume=0.1,
            added_volume=0.05,
            total_volume=0.15,
            scale_percent=0.5,
            trigger_price=1.1050,
            fill_price=1.1050,
            new_stop_loss=1.0950,
            old_stop_loss=1.0900,
            reason="Test scale-in",
            timestamp=100.0,
        )

        assert operation.ticket == 12345
        assert operation.new_ticket == 10000
        assert operation.original_volume == 0.1
        assert operation.added_volume == 0.05
        assert operation.total_volume == 0.15
        assert operation.scale_percent == 0.5
        assert operation.trigger_price == 1.1050
        assert operation.fill_price == 1.1050
        assert operation.new_stop_loss == 1.0950
        assert operation.old_stop_loss == 1.0900
        assert operation.reason == "Test scale-in"
        assert operation.timestamp == 100.0


class TestScaleInPerformance:
    """Tests for ScaleInPerformance dataclass."""

    def test_scale_in_performance_creation(self):
        """Test creating a ScaleInPerformance."""
        performance = ScaleInPerformance(
            ticket=12345,
            scaled_in_count=2,
            total_added_volume=0.1,
            final_profit_r=2.5,
            scale_in_profit_r=0.5,
            would_have_profit_r=2.0,
            improvement_r=0.5,
            timestamp=100.0,
        )

        assert performance.ticket == 12345
        assert performance.scaled_in_count == 2
        assert performance.total_added_volume == 0.1
        assert performance.final_profit_r == 2.5
        assert performance.scale_in_profit_r == 0.5
        assert performance.would_have_profit_r == 2.0
        assert performance.improvement_r == 0.5
        assert performance.timestamp == 100.0

    def test_improvement_calculation(self):
        """Test improvement calculation."""
        performance = ScaleInPerformance(
            ticket=12345,
            scaled_in_count=1,
            total_added_volume=0.05,
            final_profit_r=2.5,
            scale_in_profit_r=0.5,
            would_have_profit_r=2.0,
            improvement_r=0.5,
            timestamp=100.0,
        )

        # Improvement should be final - would_have
        assert performance.improvement_r == performance.final_profit_r - performance.would_have_profit_r
