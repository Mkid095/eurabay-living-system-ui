"""
Unit tests for PositionMonitoringLoop.

Tests the continuous monitoring loop that checks all open positions
every 5 seconds and executes all active management checks.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core import (
    PositionMonitoringLoop,
    PositionMonitoringConfig,
    MonitoringAction,
    MonitoringActionRecord,
    MonitoringLoopStats,
    ActiveTradeManager,
    TradePosition,
    MT5Position,
    TradeState,
    TrailingStopConfig,
    BreakevenConfig,
    PartialProfitConfig,
    HoldingTimeConfig,
    MarketRegime,
)


class MockMT5Connector:
    """Mock MT5 connector for testing."""

    def __init__(self):
        self.positions: list[MT5Position] = []
        self.prices: dict[str, float] = {}
        self.updates: list = []

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

    async def update_stop_loss(self, ticket: int, sl: float) -> None:
        """Update stop loss for a position."""
        self.updates.append({"action": "update_sl", "ticket": ticket, "sl": sl})

    async def close_position(self, ticket: int, lots: float) -> float:
        """Close a position."""
        self.updates.append({"action": "close", "ticket": ticket, "lots": lots})
        return self.prices.get("EURUSD", 1.0)

    async def place_order(self, symbol: str, order_type: int, volume: float,
                        price: float, sl: float, tp: float, comment: str) -> int:
        """Place an order."""
        self.updates.append({"action": "place_order", "symbol": symbol,
                           "volume": volume, "comment": comment})
        return 99999


@pytest.fixture
def mock_mt5():
    """Create a mock MT5 connector."""
    return MockMT5Connector()


@pytest.fixture
def active_trade_manager(mock_mt5):
    """Create an ActiveTradeManager with mock MT5."""
    return ActiveTradeManager(mt5_connector=mock_mt5)


@pytest.fixture
def monitoring_loop(mock_mt5, active_trade_manager):
    """Create a PositionMonitoringLoop with mocks."""
    return PositionMonitoringLoop(
        mt5_connector=mock_mt5,
        active_trade_manager=active_trade_manager
    )


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
def sample_config():
    """Create a sample monitoring configuration."""
    return PositionMonitoringConfig(
        interval_seconds=1.0,  # Short interval for testing
        enable_trailing_stop=True,
        enable_breakeven=True,
        enable_partial_profit=True,
        enable_holding_time=True,
        enable_scale_in=False,
        enable_scale_out=False,
    )


class TestPositionMonitoringLoop:
    """Test suite for PositionMonitoringLoop."""

    def test_initialization(self, monitoring_loop):
        """Test that monitoring loop initializes correctly."""
        assert monitoring_loop.is_monitoring() is False
        stats = monitoring_loop.get_statistics()
        assert stats.iterations == 0
        assert stats.positions_monitored == 0
        assert stats.actions_executed == 0

    def test_get_managers(self, monitoring_loop):
        """Test getting all manager instances."""
        managers = monitoring_loop.get_managers()

        assert "trailing_stop" in managers
        assert "breakeven" in managers
        assert "partial_profit" in managers
        assert "holding_time" in managers
        assert "scale_in" in managers
        assert "scale_out" in managers

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitoring_loop, sample_config):
        """Test starting and stopping the monitoring loop."""
        assert monitoring_loop.is_monitoring() is False

        # Start monitoring
        await monitoring_loop.start_monitoring(sample_config)
        assert monitoring_loop.is_monitoring() is True

        # Wait a bit then stop
        await asyncio.sleep(0.2)
        await monitoring_loop.stop_monitoring()
        assert monitoring_loop.is_monitoring() is False

    @pytest.mark.asyncio
    async def test_monitoring_loop_iteration(self, monitoring_loop, mock_mt5,
                                            active_trade_manager, sample_position,
                                            sample_config):
        """Test a single iteration of the monitoring loop."""
        # Set up positions
        mock_mt5.set_positions([sample_position])
        mock_mt5.set_price("EURUSD", 1.0900)

        # Add position to active trade manager
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        active_trade_manager._positions[sample_position.ticket] = position

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Start and run briefly
        await monitoring_loop.start_monitoring(sample_config)
        await asyncio.sleep(0.2)
        await monitoring_loop.stop_monitoring()

        # Check that monitoring ran
        stats = monitoring_loop.get_statistics()
        assert stats.iterations > 0
        assert stats.positions_monitored > 0

    @pytest.mark.asyncio
    async def test_trailing_stop_check(self, monitoring_loop, active_trade_manager,
                                     sample_position):
        """Test trailing stop check for a position."""
        # Create a profitable position
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.profit = 200.0  # High profit to trigger trailing
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position.ticket] = position

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Run trailing stop check
        config = TrailingStopConfig(enabled=True)
        await monitoring_loop._run_trailing_stop_check(position)

        # Note: May not trigger depending on price calculations
        # This tests that the method runs without errors

    @pytest.mark.asyncio
    async def test_breakeven_check(self, monitoring_loop, active_trade_manager,
                                  sample_position):
        """Test breakeven check for a position."""
        # Create a position with enough profit for breakeven
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.profit = 150.0  # Enough for 1.5R breakeven trigger
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position.ticket] = position

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Run breakeven check
        config = BreakevenConfig(enabled=True)
        await monitoring_loop._run_breakeven_check(position)

        # Note: May not trigger depending on risk calculations
        # This tests that the method runs without errors

    @pytest.mark.asyncio
    async def test_partial_profit_check(self, monitoring_loop, active_trade_manager,
                                      sample_position):
        """Test partial profit check for a position."""
        # Create a position with high profit
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.profit = 250.0  # High profit for 2R trigger
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position.ticket] = position

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Run partial profit check
        config = PartialProfitConfig(enabled=True)
        await monitoring_loop._run_partial_profit_check(position)

        # Note: May not trigger depending on R calculations
        # This tests that the method runs without errors

    @pytest.mark.asyncio
    async def test_holding_time_check(self, monitoring_loop, active_trade_manager,
                                    sample_position):
        """Test holding time check for a position."""
        # Create an old position
        old_entry_time = datetime.utcnow() - timedelta(hours=3)
        sample_position_old = MT5Position(
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
            entry_time=old_entry_time,
        )

        position = active_trade_manager._convert_mt5_to_trade_position(sample_position_old)
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position_old.ticket] = position

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Run holding time check (may trigger depending on default regime)
        config = HoldingTimeConfig(enabled=True, default_regime=MarketRegime.RANGING)
        await monitoring_loop._run_holding_time_check(position)

    @pytest.mark.asyncio
    async def test_scale_in_check(self, monitoring_loop, active_trade_manager,
                                sample_position, sample_config):
        """Test scale-in check for a position."""
        # Create a profitable position
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.profit = 150.0  # Enough for scale-in
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position.ticket] = position

        # Enable scale-in
        sample_config.enable_scale_in = True
        sample_config.scale_in_config.enabled = True

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Run scale-in check
        await monitoring_loop._run_scale_in_check(position)

        # Note: May not trigger depending on trend/signal quality
        # This tests that the method runs without errors

    @pytest.mark.asyncio
    async def test_scale_out_check(self, monitoring_loop, active_trade_manager,
                                 sample_position, sample_config):
        """Test scale-out check for a position."""
        # Create a profitable position
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.profit = 250.0  # High profit for scale-out
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position.ticket] = position

        # Enable scale-out
        sample_config.enable_scale_out = True
        sample_config.scale_out_config.enabled = True

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Run scale-out check
        await monitoring_loop._run_scale_out_check(position)

        # Note: May not trigger depending on R calculations
        # This tests that the method runs without errors

    @pytest.mark.asyncio
    async def test_action_recording(self, monitoring_loop):
        """Test that actions are recorded correctly."""
        # Create a mock action
        action = MonitoringActionRecord(
            ticket=12345,
            action_type=MonitoringAction.TRAILING_STOP,
            description="Test action",
            result="success",
            timestamp=datetime.utcnow(),
        )

        # Record action
        monitoring_loop._record_action(action)

        # Check action was recorded
        history = monitoring_loop.get_action_history()
        assert len(history) == 1
        assert history[0].ticket == 12345
        assert history[0].action_type == MonitoringAction.TRAILING_STOP

        # Check statistics updated
        stats = monitoring_loop.get_statistics()
        assert stats.actions_executed == 1

    @pytest.mark.asyncio
    async def test_action_callback(self, monitoring_loop):
        """Test action callback functionality."""
        # Track callbacks
        callback_calls = []

        def test_callback(action):
            callback_calls.append(action)

        monitoring_loop.set_action_callback(test_callback)

        # Create and record action
        action = MonitoringActionRecord(
            ticket=12345,
            action_type=MonitoringAction.BREAKEVEN,
            description="Test callback",
            result="success",
            timestamp=datetime.utcnow(),
        )

        monitoring_loop._record_action(action)

        # Check callback was triggered
        assert len(callback_calls) == 1
        assert callback_calls[0].ticket == 12345

    @pytest.mark.asyncio
    async def test_get_action_history_filtered(self, monitoring_loop):
        """Test getting action history filtered by ticket."""
        # Create multiple actions
        actions = [
            MonitoringActionRecord(
                ticket=12345,
                action_type=MonitoringAction.TRAILING_STOP,
                description="Action 1",
                result="success",
                timestamp=datetime.utcnow(),
            ),
            MonitoringActionRecord(
                ticket=12346,
                action_type=MonitoringAction.BREAKEVEN,
                description="Action 2",
                result="success",
                timestamp=datetime.utcnow(),
            ),
            MonitoringActionRecord(
                ticket=12345,
                action_type=MonitoringAction.PARTIAL_PROFIT,
                description="Action 3",
                result="success",
                timestamp=datetime.utcnow(),
            ),
        ]

        for action in actions:
            monitoring_loop._record_action(action)

        # Get all history
        all_history = monitoring_loop.get_action_history()
        assert len(all_history) == 3

        # Get filtered history
        filtered_history = monitoring_loop.get_action_history(ticket=12345)
        assert len(filtered_history) == 2
        assert all(a.ticket == 12345 for a in filtered_history)

    @pytest.mark.asyncio
    async def test_clear_action_history(self, monitoring_loop):
        """Test clearing action history."""
        # Create and record action
        action = MonitoringActionRecord(
            ticket=12345,
            action_type=MonitoringAction.TRAILING_STOP,
            description="Test action",
            result="success",
            timestamp=datetime.utcnow(),
        )

        monitoring_loop._record_action(action)

        # Verify action was recorded
        assert len(monitoring_loop.get_action_history()) == 1

        # Clear history
        monitoring_loop.clear_action_history()

        # Verify history is cleared
        assert len(monitoring_loop.get_action_history()) == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_monitoring_loop(self, monitoring_loop,
                                                    mock_mt5, active_trade_manager,
                                                    sample_config):
        """Test error handling in the monitoring loop."""
        # Set up to cause an error (empty positions list is fine)
        mock_mt5.set_positions([])

        # Start monitoring
        await monitoring_loop.start_monitoring(sample_config)

        # Wait for iterations
        await asyncio.sleep(0.2)

        # Stop monitoring
        await monitoring_loop.stop_monitoring()

        # Check that monitoring completed despite no positions
        assert monitoring_loop.get_statistics().iterations > 0

    @pytest.mark.asyncio
    async def test_process_position_with_all_checks(self, monitoring_loop,
                                                   active_trade_manager,
                                                   sample_position):
        """Test processing a position through all management checks."""
        # Add position to active trade manager
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.current_price = 1.0900
        active_trade_manager._positions[sample_position.ticket] = position

        # Track actions
        actions = []
        monitoring_loop.set_action_callback(lambda a: actions.append(a))

        # Process position
        await monitoring_loop._process_position(sample_position)

        # Check that position was processed without errors
        # Actions may or may not be recorded depending on triggers

    @pytest.mark.asyncio
    async def test_check_sl_tp_hits(self, monitoring_loop, active_trade_manager,
                                   sample_position):
        """Test SL/TP hit detection."""
        # Add position to active trade manager
        position = active_trade_manager._convert_mt5_to_trade_position(sample_position)
        position.profit = -500.0  # Large loss indicating SL hit
        position.current_price = 1.0750
        active_trade_manager._positions[sample_position.ticket] = position

        # Check SL/TP hits
        result = await monitoring_loop._check_sl_tp_hits(position)

        # Should detect SL hit and return True
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_positions_monitoring(self, monitoring_loop, mock_mt5,
                                                active_trade_manager,
                                                sample_config):
        """Test monitoring multiple positions simultaneously."""
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

        # Add positions to active trade manager
        for mt5_pos in positions:
            position = active_trade_manager._convert_mt5_to_trade_position(mt5_pos)
            active_trade_manager._positions[mt5_pos.ticket] = position

        # Start monitoring
        await monitoring_loop.start_monitoring(sample_config)
        await asyncio.sleep(0.2)
        await monitoring_loop.stop_monitoring()

        # Check statistics
        stats = monitoring_loop.get_statistics()
        assert stats.positions_monitored >= 2  # At least 2 positions monitored


class TestPositionMonitoringConfig:
    """Test suite for PositionMonitoringConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PositionMonitoringConfig()

        assert config.interval_seconds == 5.0
        assert config.enable_trailing_stop is True
        assert config.enable_breakeven is True
        assert config.enable_partial_profit is True
        assert config.enable_holding_time is True
        assert config.enable_scale_in is False
        assert config.enable_scale_out is False
        assert config.default_regime == MarketRegime.RANGING

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PositionMonitoringConfig(
            interval_seconds=10.0,
            enable_trailing_stop=False,
            enable_scale_in=True,
        )

        assert config.interval_seconds == 10.0
        assert config.enable_trailing_stop is False
        assert config.enable_scale_in is True

    def test_config_post_init(self):
        """Test that post-init creates default configs."""
        config = PositionMonitoringConfig()

        assert config.trailing_stop_config is not None
        assert config.breakeven_config is not None
        assert config.partial_profit_config is not None
        assert config.holding_time_config is not None
        assert config.scale_in_config is not None
        assert config.scale_out_config is not None


class TestMonitoringActionRecord:
    """Test suite for MonitoringActionRecord."""

    def test_action_record_creation(self):
        """Test creating an action record."""
        record = MonitoringActionRecord(
            ticket=12345,
            action_type=MonitoringAction.TRAILING_STOP,
            description="Trailing stop updated",
            result="success",
            timestamp=datetime.utcnow(),
        )

        assert record.ticket == 12345
        assert record.action_type == MonitoringAction.TRAILING_STOP
        assert record.description == "Trailing stop updated"
        assert record.result == "success"


class TestMonitoringLoopStats:
    """Test suite for MonitoringLoopStats."""

    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = MonitoringLoopStats()

        assert stats.iterations == 0
        assert stats.positions_monitored == 0
        assert stats.actions_executed == 0
        assert stats.errors == 0
        assert stats.start_time is None
        assert stats.last_iteration_time is None

    def test_stats_updates(self):
        """Test updating statistics."""
        stats = MonitoringLoopStats()
        stats.iterations = 5
        stats.positions_monitored = 10
        stats.actions_executed = 3
        stats.errors = 1
        stats.start_time = datetime.utcnow()
        stats.last_iteration_time = datetime.utcnow()

        assert stats.iterations == 5
        assert stats.positions_monitored == 10
        assert stats.actions_executed == 3
        assert stats.errors == 1
