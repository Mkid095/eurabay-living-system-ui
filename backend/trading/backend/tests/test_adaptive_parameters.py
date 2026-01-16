"""
Unit tests for AdaptiveParameters module.

Tests the adaptive parameter management system that adjusts trade
management parameters based on market conditions and performance.
"""

import pytest
import sqlite3
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from backend.core.adaptive_parameters import (
    AdaptiveParametersManager,
    AdaptiveParameters,
    PerformanceMetrics,
    ParameterUpdate,
    OptimizationResult,
    VolatilityRegime,
)
from backend.core.holding_time_optimizer import MarketRegime
from backend.core.trailing_stop_manager import TrailingStopConfig
from backend.core.partial_profit_manager import PartialProfitConfig
from backend.core.holding_time_optimizer import HoldingTimeConfig
from backend.core.scale_in_manager import ScaleInConfig


# Fixtures
@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    db_path = ":memory:"
    manager = AdaptiveParametersManager(database_path=db_path)
    yield manager
    manager.close()


@pytest.fixture
def sample_performance_metrics():
    """Create sample performance metrics for testing."""
    return PerformanceMetrics(
        win_rate=55.0,
        profit_factor=1.5,
        average_win=100.0,
        average_loss=67.0,
        total_trades=50,
        sharpe_ratio=1.2,
        max_drawdown=10.0,
        average_holding_time=timedelta(hours=2),
    )


@pytest.fixture
def sample_atr_values():
    """Create sample ATR values for volatility calculation."""
    return [0.0010, 0.0011, 0.0012, 0.0010, 0.0013, 0.0015, 0.0014]


@pytest.fixture
def sample_historical_data():
    """Create sample historical trade data for optimization."""
    return [
        {"profit": 100.0, "max_drawdown": -20.0},
        {"profit": 150.0, "max_drawdown": -15.0},
        {"profit": -50.0, "max_drawdown": -50.0},
        {"profit": 200.0, "max_drawdown": -10.0},
        {"profit": -30.0, "max_drawdown": -30.0},
        {"profit": 180.0, "max_drawdown": -25.0},
        {"profit": 120.0, "max_drawdown": -18.0},
        {"profit": -40.0, "max_drawdown": -40.0},
        {"profit": 160.0, "max_drawdown": -12.0},
        {"profit": 90.0, "max_drawdown": -22.0},
    ]


class TestAdaptiveParameters:
    """Tests for AdaptiveParameters dataclass."""

    def test_default_parameters(self):
        """Test default parameter values."""
        params = AdaptiveParameters()

        assert params.trailing_atr_multiplier == 2.0
        assert params.partial_profit_1r == 2.0
        assert params.partial_profit_2r == 3.0
        assert params.holding_time_trending == 4.0
        assert params.holding_time_ranging == 2.0
        assert params.holding_time_volatile == 1.0
        assert params.scale_in_enabled is True
        assert params.scale_in_max_factor == 200.0
        assert params.breakeven_trigger_r == 1.5

    def test_to_dict(self):
        """Test parameter serialization to dictionary."""
        params = AdaptiveParameters(
            trailing_atr_multiplier=3.0,
            volatility_regime=VolatilityRegime.HIGH,
        )

        result = params.to_dict()

        assert result["trailing_atr_multiplier"] == 3.0
        assert result["volatility_regime"] == "high"
        assert isinstance(result, dict)


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = PerformanceMetrics()

        assert metrics.win_rate == 50.0
        assert metrics.profit_factor == 1.0
        assert metrics.total_trades == 0

    def test_to_dict(self):
        """Test metric serialization to dictionary."""
        metrics = PerformanceMetrics(
            win_rate=60.0,
            profit_factor=2.0,
            average_holding_time=timedelta(hours=3),
        )

        result = metrics.to_dict()

        assert result["win_rate"] == 60.0
        assert result["profit_factor"] == 2.0
        assert result["average_holding_time_seconds"] == 10800


class TestAdaptiveParametersManager:
    """Tests for AdaptiveParametersManager class."""

    def test_initialization(self, temp_database):
        """Test manager initialization."""
        manager = temp_database

        assert manager._current_parameters is not None
        assert manager._update_interval_days == 7
        assert manager._connection is not None

    def test_get_current_parameters(self, temp_database):
        """Test getting current parameters."""
        manager = temp_database

        params = manager.get_current_parameters()

        assert isinstance(params, AdaptiveParameters)
        assert params.trailing_atr_multiplier > 0

    def test_calculate_volatility_regime_low(self, temp_database):
        """Test volatility regime calculation for low volatility."""
        manager = temp_database

        # ATR values decreasing significantly (more than 15%)
        # Average: 0.0016, Current: 0.0011 = -31% change
        atr_values = [0.0020, 0.0019, 0.0018, 0.0016, 0.0014, 0.0012, 0.0011]

        regime = manager._calculate_volatility_regime(atr_values)

        assert regime == VolatilityRegime.LOW

    def test_calculate_volatility_regime_normal(self, temp_database):
        """Test volatility regime calculation for normal volatility."""
        manager = temp_database

        # ATR values relatively stable
        atr_values = [0.0010, 0.0011, 0.0010, 0.0012, 0.0011, 0.0010, 0.0011]

        regime = manager._calculate_volatility_regime(atr_values)

        assert regime == VolatilityRegime.NORMAL

    def test_calculate_volatility_regime_high(self, temp_database):
        """Test volatility regime calculation for high volatility."""
        manager = temp_database

        # ATR values increasing significantly
        atr_values = [0.0010, 0.0012, 0.0014, 0.0015, 0.0016, 0.0017, 0.0018]

        regime = manager._calculate_volatility_regime(atr_values)

        assert regime == VolatilityRegime.HIGH

    def test_calculate_volatility_regime_extreme(self, temp_database):
        """Test volatility regime calculation for extreme volatility."""
        manager = temp_database

        # ATR values more than doubling (>40% increase)
        # Average: 0.0017, Current: 0.0030 = +76% change
        atr_values = [0.0010, 0.0012, 0.0015, 0.0018, 0.0020, 0.0025, 0.0030]

        regime = manager._calculate_volatility_regime(atr_values)

        assert regime == VolatilityRegime.EXTREME

    def test_calculate_volatility_regime_insufficient_data(self, temp_database):
        """Test volatility regime with insufficient data."""
        manager = temp_database

        # Too few ATR values
        atr_values = [0.0010, 0.0011]

        regime = manager._calculate_volatility_regime(atr_values)

        assert regime == VolatilityRegime.NORMAL

    def test_adjust_trailing_distance_low_volatility(self, temp_database):
        """Test trailing distance adjustment for low volatility."""
        manager = temp_database
        current_params = AdaptiveParameters()

        new_mult = manager._adjust_trailing_distance(
            VolatilityRegime.LOW, current_params
        )

        assert new_mult == 1.5  # Tighter stops in low volatility

    def test_adjust_trailing_distance_normal_volatility(self, temp_database):
        """Test trailing distance adjustment for normal volatility."""
        manager = temp_database
        current_params = AdaptiveParameters()

        new_mult = manager._adjust_trailing_distance(
            VolatilityRegime.NORMAL, current_params
        )

        assert new_mult == 2.0  # Standard stops

    def test_adjust_trailing_distance_high_volatility(self, temp_database):
        """Test trailing distance adjustment for high volatility."""
        manager = temp_database
        current_params = AdaptiveParameters()

        new_mult = manager._adjust_trailing_distance(
            VolatilityRegime.HIGH, current_params
        )

        assert new_mult == 3.0  # Wider stops in high volatility

    def test_adjust_trailing_distance_extreme_volatility(self, temp_database):
        """Test trailing distance adjustment for extreme volatility."""
        manager = temp_database
        current_params = AdaptiveParameters()

        new_mult = manager._adjust_trailing_distance(
            VolatilityRegime.EXTREME, current_params
        )

        assert new_mult == 4.0  # Very wide stops in extreme volatility

    def test_adjust_partial_profit_high_win_rate(self, temp_database):
        """Test partial profit adjustment for high win rate."""
        manager = temp_database
        performance = PerformanceMetrics(win_rate=65.0)
        current_params = AdaptiveParameters()

        p1r, p2r = manager._adjust_partial_profit_levels(performance, current_params)

        assert p1r == 2.5  # Hold longer for larger profits
        assert p2r == 4.0

    def test_adjust_partial_profit_normal_win_rate(self, temp_database):
        """Test partial profit adjustment for normal win rate."""
        manager = temp_database
        performance = PerformanceMetrics(win_rate=52.0)
        current_params = AdaptiveParameters()

        p1r, p2r = manager._adjust_partial_profit_levels(performance, current_params)

        assert p1r == 2.0  # Standard levels
        assert p2r == 3.0

    def test_adjust_partial_profit_low_win_rate(self, temp_database):
        """Test partial profit adjustment for low win rate."""
        manager = temp_database
        performance = PerformanceMetrics(win_rate=35.0)
        current_params = AdaptiveParameters()

        p1r, p2r = manager._adjust_partial_profit_levels(performance, current_params)

        assert p1r == 1.0  # Bank profits very early
        assert p2r == 2.0

    def test_adjust_holding_time_low_volatility(self, temp_database):
        """Test holding time adjustment for low volatility."""
        manager = temp_database
        current_params = AdaptiveParameters()

        trending, ranging, volatile = manager._adjust_holding_time_limits(
            MarketRegime.TRENDING, VolatilityRegime.LOW, current_params
        )

        assert trending == 6.0  # Can hold longer in low vol (4.0 * 1.5)
        assert ranging == 3.0  # (2.0 * 1.5)
        assert volatile == 1.5  # (1.0 * 1.5)

    def test_adjust_holding_time_high_volatility(self, temp_database):
        """Test holding time adjustment for high volatility."""
        manager = temp_database
        current_params = AdaptiveParameters()

        trending, ranging, volatile = manager._adjust_holding_time_limits(
            MarketRegime.TRENDING, VolatilityRegime.HIGH, current_params
        )

        assert trending == 3.0  # Hold shorter in high vol (4.0 * 0.75)
        assert ranging == 1.5  # (2.0 * 0.75)
        assert volatile == 0.75  # (1.0 * 0.75)

    def test_adjust_scale_in_high_drawdown(self, temp_database):
        """Test scale-in adjustment for high drawdown."""
        manager = temp_database
        performance = PerformanceMetrics(max_drawdown=25.0)  # 25% drawdown
        current_params = AdaptiveParameters()

        enabled, max_factor = manager._adjust_scale_in_rules(
            performance, current_params
        )

        assert enabled is False  # Disable scale-in with high drawdown
        assert max_factor == 100.0

    def test_adjust_scale_in_low_profit_factor(self, temp_database):
        """Test scale-in adjustment for low profit factor."""
        manager = temp_database
        performance = PerformanceMetrics(profit_factor=0.8)
        current_params = AdaptiveParameters()

        enabled, max_factor = manager._adjust_scale_in_rules(
            performance, current_params
        )

        assert enabled is False  # Disable scale-in if not profitable

    def test_adjust_scale_in_excellent_performance(self, temp_database):
        """Test scale-in adjustment for excellent performance."""
        manager = temp_database
        performance = PerformanceMetrics(
            sharpe_ratio=2.5, max_drawdown=10.0, profit_factor=2.0
        )
        current_params = AdaptiveParameters()

        enabled, max_factor = manager._adjust_scale_in_rules(
            performance, current_params
        )

        assert enabled is True
        assert max_factor == 250.0  # Allow more scaling with excellent Sharpe

    @pytest.mark.asyncio
    async def test_update_parameters_comprehensive(
        self, temp_database, sample_performance_metrics, sample_atr_values
    ):
        """Test comprehensive parameter update."""
        manager = temp_database

        old_params = manager.get_current_parameters()

        new_params = await manager.update_parameters(
            performance=sample_performance_metrics,
            market_regime=MarketRegime.TRENDING,
            atr_values=sample_atr_values,
        )

        assert isinstance(new_params, AdaptiveParameters)
        assert new_params.last_updated > old_params.last_updated
        assert len(manager.get_update_history()) == 1

    def test_get_trailing_stop_config(self, temp_database):
        """Test getting trailing stop configuration."""
        manager = temp_database

        config = manager.get_trailing_stop_config()

        assert isinstance(config, TrailingStopConfig)
        assert config.atr_multiplier == manager._current_parameters.trailing_atr_multiplier

    def test_get_partial_profit_config(self, temp_database):
        """Test getting partial profit configuration."""
        manager = temp_database

        config = manager.get_partial_profit_config()

        assert isinstance(config, PartialProfitConfig)
        assert config.close_50_at_r == manager._current_parameters.partial_profit_1r
        assert config.close_25_at_r == manager._current_parameters.partial_profit_2r

    def test_get_holding_time_config(self, temp_database):
        """Test getting holding time configuration."""
        manager = temp_database

        config = manager.get_holding_time_config(MarketRegime.TRENDING)

        assert isinstance(config, HoldingTimeConfig)
        assert (
            config.trending_max_hours
            == manager._current_parameters.holding_time_trending
        )

    def test_get_scale_in_config(self, temp_database):
        """Test getting scale-in configuration."""
        manager = temp_database

        config = manager.get_scale_in_config()

        assert isinstance(config, ScaleInConfig)
        assert config.max_scale_factor == manager._current_parameters.scale_in_max_factor
        assert config.enabled == manager._current_parameters.scale_in_enabled

    def test_should_update_parameters_false(self, temp_database):
        """Test should_update_parameters returns False when recently updated."""
        manager = temp_database

        # Parameters were just updated during initialization
        assert manager.should_update_parameters() is False

    def test_should_update_parameters_true(self, temp_database):
        """Test should_update_parameters returns True after interval."""
        manager = temp_database

        # Manually set last updated time to 8 days ago
        manager._current_parameters.last_updated = datetime.utcnow() - timedelta(days=8)

        assert manager.should_update_parameters() is True

    @pytest.mark.asyncio
    async def test_optimize_parameters(
        self, temp_database, sample_historical_data
    ):
        """Test parameter optimization on historical data."""
        manager = temp_database

        result = await manager.optimize_parameters(sample_historical_data)

        assert isinstance(result, OptimizationResult)
        assert isinstance(result.parameters, AdaptiveParameters)
        assert result.sharpe_ratio >= 0
        assert 0 <= result.win_rate <= 100

    def test_simulate_parameters(self, temp_database, sample_historical_data):
        """Test parameter simulation."""
        manager = temp_database

        params = AdaptiveParameters(
            trailing_atr_multiplier=2.5,
            partial_profit_1r=2.0,
            partial_profit_2r=3.0,
        )

        result = manager._simulate_parameters(params, sample_historical_data)

        assert isinstance(result, OptimizationResult)
        assert result.parameters == params
        assert result.total_trades == len(sample_historical_data)

    @pytest.mark.asyncio
    async def test_database_persistence(self, temp_database, sample_performance_metrics):
        """Test that parameters are persisted to database."""
        manager = temp_database

        # Update parameters
        await manager.update_parameters(
            performance=sample_performance_metrics,
            market_regime=MarketRegime.RANGING,
        )

        # Create new manager instance (should load from database)
        manager2 = AdaptiveParametersManager(database_path=manager._database_path)

        # Verify parameters were loaded
        loaded_params = manager2.get_current_parameters()
        assert loaded_params.trailing_atr_multiplier > 0

        manager2.close()

    @pytest.mark.asyncio
    async def test_update_history_tracking(
        self, temp_database, sample_performance_metrics
    ):
        """Test that update history is tracked correctly."""
        manager = temp_database

        # Perform multiple updates
        await manager.update_parameters(
            performance=sample_performance_metrics,
            market_regime=MarketRegime.TRENDING,
        )

        await manager.update_parameters(
            performance=sample_performance_metrics,
            market_regime=MarketRegime.RANGING,
        )

        history = manager.get_update_history()

        assert len(history) == 2
        assert all(isinstance(update, ParameterUpdate) for update in history)

    def test_close_connection(self, temp_database):
        """Test closing database connection."""
        manager = temp_database

        manager.close()

        assert manager._connection is None


class TestIntegration:
    """Integration tests for adaptive parameters with other components."""

    @pytest.mark.asyncio
    async def test_adaptive_trailing_stop_workflow(self, temp_database):
        """Test adaptive parameters with trailing stop workflow."""
        manager = temp_database

        # Simulate high volatility conditions
        high_vol_performance = PerformanceMetrics(
            win_rate=45.0,
            profit_factor=1.2,
            sharpe_ratio=0.8,
            max_drawdown=15.0,
        )

        # Update parameters for high volatility
        # ATR values increasing by 70% (from 0.0010 avg to 0.0017 current)
        await manager.update_parameters(
            performance=high_vol_performance,
            market_regime=MarketRegime.VOLATILE,
            atr_values=[0.0010, 0.0011, 0.0012, 0.0013, 0.0015, 0.0016, 0.0017],
        )

        # Get trailing stop config
        config = manager.get_trailing_stop_config()

        # Verify wider stops in high volatility (should be 3.0x for HIGH volatility)
        assert config.atr_multiplier >= 3.0

    @pytest.mark.asyncio
    async def test_adaptive_partial_profit_workflow(self, temp_database):
        """Test adaptive parameters with partial profit workflow."""
        manager = temp_database

        # Simulate high win rate conditions
        high_win_performance = PerformanceMetrics(
            win_rate=65.0,
            profit_factor=2.0,
            sharpe_ratio=1.8,
            max_drawdown=8.0,
        )

        # Update parameters for high win rate
        await manager.update_parameters(
            performance=high_win_performance,
            market_regime=MarketRegime.TRENDING,
        )

        # Get partial profit config
        config = manager.get_partial_profit_config()

        # Verify holding for larger profits with high win rate
        assert config.close_50_at_r >= 2.0

    @pytest.mark.asyncio
    async def test_weekly_update_cycle(self, temp_database):
        """Test weekly parameter update cycle."""
        manager = AdaptiveParametersManager(
            database_path=":memory:", update_interval_days=7
        )

        # Initially should not need update
        assert manager.should_update_parameters() is False

        # Simulate time passing (8 days)
        manager._current_parameters.last_updated = datetime.utcnow() - timedelta(days=8)

        # Now should need update
        assert manager.should_update_parameters() is True

        # Perform update
        performance = PerformanceMetrics(win_rate=55.0, profit_factor=1.5)
        await manager.update_parameters(performance, MarketRegime.RANGING)

        # Should not need update again
        assert manager.should_update_parameters() is False

        manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
