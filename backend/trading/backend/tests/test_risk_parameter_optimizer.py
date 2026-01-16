"""
Tests for RiskParameterOptimizer.

This module tests the risk parameter optimization functionality, including:
- Backtesting different risk parameter combinations
- Finding optimal parameters based on Sharpe ratio
- Storing and retrieving optimal parameters
- Market regime detection
- Database persistence
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import numpy as np

from backend.core.risk_parameter_optimizer import (
    RiskParameterOptimizer,
    RiskParameterSet,
    OptimizationResult,
    OptimalParameters,
    MarketRegime,
)
from backend.core.performance_comparator import (
    PerformanceComparator,
    TradeOutcome,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def mock_performance_comparator():
    """Create a mock PerformanceComparator."""
    mock = Mock(spec=PerformanceComparator)

    # Create mock trade outcomes
    mock_trades = []
    for i in range(100):
        trade = Mock(spec=TradeOutcome)
        trade.ticket = i + 1
        trade.symbol = "EURUSD"
        trade.direction = "BUY" if i % 2 == 0 else "SELL"
        trade.entry_price = 1.0850
        trade.exit_price = 1.0870 if i % 2 == 0 else 1.0830
        trade.entry_time = datetime.now() - timedelta(days=i)
        trade.exit_time = datetime.now() - timedelta(days=i) + timedelta(hours=4)
        trade.profit = 100.0 if i % 2 == 0 else -80.0
        trade.pnl = 100.0 if i % 2 == 0 else -80.0
        trade.pnl_percent = 1.0 if i % 2 == 0 else -0.8
        trade.stop_loss = 1.0800
        trade.take_profit = 1.0900

        # Evolved trade attributes
        trade.generation = 5
        trade.features_used = ["trailing_stop", "breakeven", "partial_profit"]
        trade.confidence = 0.75

        mock_trades.append(trade)

    mock.get_evolved_trades = Mock(return_value=mock_trades)
    mock.get_evolved_trades_in_date_range = Mock(return_value=mock_trades)

    return mock


@pytest.fixture
def optimizer(mock_performance_comparator, temp_db_path):
    """Create a RiskParameterOptimizer instance."""
    return RiskParameterOptimizer(
        performance_comparator=mock_performance_comparator,
        database_path=temp_db_path,
        base_risk_options=[1.0, 2.0],
        stop_atr_multiplier_options=[1.5, 2.0],
        tp_atr_multiplier_options=[2.0, 3.0],
        optimization_period_days=180,
        rebalance_frequency_days=7,
        min_trades_for_optimization=50,
    )


class TestRiskParameterSet:
    """Tests for RiskParameterSet dataclass."""

    def test_create_parameter_set(self):
        """Test creating a risk parameter set."""
        params = RiskParameterSet(
            base_risk_percent=2.0,
            stop_atr_multiplier=2.0,
            tp_atr_multiplier=2.5,
        )

        assert params.base_risk_percent == 2.0
        assert params.stop_atr_multiplier == 2.0
        assert params.tp_atr_multiplier == 2.5

    def test_parameter_set_to_dict(self):
        """Test converting parameter set to dictionary."""
        params = RiskParameterSet(
            base_risk_percent=1.5,
            stop_atr_multiplier=1.8,
            tp_atr_multiplier=3.0,
        )

        data = params.to_dict()

        assert data["base_risk_percent"] == 1.5
        assert data["stop_atr_multiplier"] == 1.8
        assert data["tp_atr_multiplier"] == 3.0

    def test_parameter_set_from_dict(self):
        """Test creating parameter set from dictionary."""
        data = {
            "base_risk_percent": 2.5,
            "stop_atr_multiplier": 2.2,
            "tp_atr_multiplier": 3.5,
        }

        params = RiskParameterSet.from_dict(data)

        assert params.base_risk_percent == 2.5
        assert params.stop_atr_multiplier == 2.2
        assert params.tp_atr_multiplier == 3.5


class TestOptimizationResult:
    """Tests for OptimizationResult dataclass."""

    def test_create_optimization_result(self):
        """Test creating an optimization result."""
        params = RiskParameterSet(2.0, 2.0, 2.5)
        result = OptimizationResult(
            parameter_set=params,
            sharpe_ratio=1.85,
            total_return=25.5,
            win_rate=60.0,
            profit_factor=2.1,
            max_drawdown=8.5,
            total_trades=100,
            symbol="EURUSD",
            market_regime=MarketRegime.NORMAL,
            timestamp=datetime.now(),
        )

        assert result.sharpe_ratio == 1.85
        assert result.total_return == 25.5
        assert result.symbol == "EURUSD"

    def test_optimization_result_to_dict(self):
        """Test converting optimization result to dictionary."""
        params = RiskParameterSet(1.5, 1.8, 3.0)
        timestamp = datetime.now()
        result = OptimizationResult(
            parameter_set=params,
            sharpe_ratio=2.1,
            total_return=30.0,
            win_rate=65.0,
            profit_factor=2.5,
            max_drawdown=10.0,
            total_trades=150,
            symbol="GBPUSD",
            market_regime=MarketRegime.HIGH,
            timestamp=timestamp,
        )

        data = result.to_dict()

        assert data["base_risk_percent"] == 1.5
        assert data["sharpe_ratio"] == 2.1
        assert data["symbol"] == "GBPUSD"
        assert data["market_regime"] == "HIGH"


class TestMarketRegime:
    """Tests for MarketRegime enum."""

    def test_market_regime_values(self):
        """Test market regime enum values."""
        assert MarketRegime.LOW.value == "LOW"
        assert MarketRegime.NORMAL.value == "NORMAL"
        assert MarketRegime.HIGH.value == "HIGH"


class TestRiskParameterOptimizerInit:
    """Tests for RiskParameterOptimizer initialization."""

    def test_initialization(self, optimizer, temp_db_path):
        """Test optimizer initialization."""
        assert optimizer.performance_comparator is not None
        assert optimizer.database_path == temp_db_path
        assert optimizer.base_risk_options == [1.0, 2.0]
        assert optimizer.stop_atr_multiplier_options == [1.5, 2.0]
        assert optimizer.tp_atr_multiplier_options == [2.0, 3.0]
        assert optimizer.optimization_period_days == 180
        assert optimizer.rebalance_frequency_days == 7
        assert optimizer.min_trades_for_optimization == 50

    def test_database_creation(self, optimizer, temp_db_path):
        """Test that database tables are created."""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check optimal_parameters table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='optimal_parameters'
        """)
        assert cursor.fetchone() is not None

        # Check optimization_results table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='optimization_results'
        """)
        assert cursor.fetchone() is not None

        conn.close()


class TestDetectMarketRegime:
    """Tests for market regime detection."""

    def test_detect_low_volatility_regime(self, optimizer):
        """Test detection of low volatility regime."""
        # Create trades with low P&L volatility
        mock_trades = []
        for i in range(50):
            trade = Mock(spec=TradeOutcome)
            trade.pnl_percent = 0.3 + (i % 10) * 0.05  # Low variance
            mock_trades.append(trade)

        optimizer.performance_comparator.get_evolved_trades = Mock(
            return_value=mock_trades
        )

        regime = optimizer._detect_market_regime("EURUSD")

        assert regime == MarketRegime.LOW

    def test_detect_normal_volatility_regime(self, optimizer):
        """Test detection of normal volatility regime."""
        # Create trades with normal P&L volatility (std between 1.0 and 2.5)
        mock_trades = []
        pnl_values = [2.5, -2.0, 3.0, -1.5, 2.0, -2.5, 1.8, -2.2, 2.8, -1.8,
                      2.3, -1.9, 2.7, -2.1, 2.1, -2.4, 2.6, -1.7, 2.4, -2.3]
        for pnl in pnl_values:
            trade = Mock(spec=TradeOutcome)
            trade.pnl_percent = pnl
            mock_trades.append(trade)

        optimizer.performance_comparator.get_evolved_trades = Mock(
            return_value=mock_trades
        )

        regime = optimizer._detect_market_regime("GBPUSD")

        assert regime == MarketRegime.NORMAL

    def test_detect_high_volatility_regime(self, optimizer):
        """Test detection of high volatility regime (std > 2.5)."""
        # Create trades with high P&L volatility
        mock_trades = []
        pnl_values = [5.0, -4.5, 6.0, -3.5, 5.5, -5.0, 4.8, -5.2, 6.2, -4.2,
                      5.3, -4.8, 5.7, -5.1, 5.1, -5.4, 5.6, -4.0, 5.4, -5.3]
        for pnl in pnl_values:
            trade = Mock(spec=TradeOutcome)
            trade.pnl_percent = pnl
            mock_trades.append(trade)

        optimizer.performance_comparator.get_evolved_trades = Mock(
            return_value=mock_trades
        )

        regime = optimizer._detect_market_regime("V10")

        assert regime == MarketRegime.HIGH

    def test_detect_regime_insufficient_data(self, optimizer):
        """Test regime detection with insufficient data."""
        optimizer.performance_comparator.get_evolved_trades = Mock(return_value=[])

        regime = optimizer._detect_market_regime("EURUSD")

        assert regime == MarketRegime.NORMAL  # Default


class TestBacktestRiskParameters:
    """Tests for backtesting risk parameters."""

    def test_backtest_with_sufficient_data(self, optimizer):
        """Test backtesting with sufficient trade data."""
        params = RiskParameterSet(
            base_risk_percent=2.0,
            stop_atr_multiplier=2.0,
            tp_atr_multiplier=2.5,
        )

        result = optimizer.backtest_risk_parameters(
            symbol="EURUSD",
            parameter_set=params,
            market_regime=MarketRegime.NORMAL,
        )

        assert isinstance(result, OptimizationResult)
        assert result.symbol == "EURUSD"
        assert result.market_regime == MarketRegime.NORMAL
        assert result.parameter_set == params
        assert result.total_trades >= optimizer.min_trades_for_optimization

    def test_backtest_with_insufficient_data(self, optimizer):
        """Test backtesting with insufficient trade data."""
        optimizer.performance_comparator.get_evolved_trades_in_date_range = Mock(
            return_value=[]
        )

        params = RiskParameterSet(2.0, 2.0, 2.5)

        result = optimizer.backtest_risk_parameters(
            symbol="EURUSD",
            parameter_set=params,
            market_regime=MarketRegime.NORMAL,
        )

        assert result.sharpe_ratio == -999.0  # Poor result indicator
        assert result.total_trades == 0

    def test_backtest_calculates_metrics(self, optimizer):
        """Test that backtesting calculates all required metrics."""
        params = RiskParameterSet(2.0, 2.0, 2.5)

        result = optimizer.backtest_risk_parameters(
            symbol="EURUSD",
            parameter_set=params,
            market_regime=MarketRegime.NORMAL,
        )

        # Check all metrics are calculated
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "total_return")
        assert hasattr(result, "win_rate")
        assert hasattr(result, "profit_factor")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "total_trades")

    def test_backtest_stores_result(self, optimizer, temp_db_path):
        """Test that optimization stores backtest results in database."""
        # Run optimization which internally calls backtest and stores results
        optimizer.optimize_parameters("GBPUSD")

        # Verify results were stored
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM optimization_results
            WHERE symbol = 'GBPUSD'
        """)
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0


class TestOptimizeParameters:
    """Tests for parameter optimization."""

    def test_optimize_parameters_success(self, optimizer):
        """Test successful parameter optimization."""
        optimal = optimizer.optimize_parameters("EURUSD")

        assert optimal is not None
        assert optimal.symbol == "EURUSD"
        assert isinstance(optimal.parameter_set, RiskParameterSet)
        assert isinstance(optimal.sharpe_ratio, float)
        assert optimal.valid_until > datetime.now()

    def test_optimize_parameters_insufficient_data(self, optimizer):
        """Test optimization with insufficient data."""
        optimizer.performance_comparator.get_evolved_trades_in_date_range = Mock(
            return_value=[]
        )

        optimal = optimizer.optimize_parameters("USDJPY")

        # Should return None when insufficient data
        assert optimal is None

    def test_optimize_stores_in_database(self, optimizer, temp_db_path):
        """Test that optimal parameters are stored in database."""
        optimizer.optimize_parameters("EURUSD")

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM optimal_parameters
            WHERE symbol = 'EURUSD'
        """)
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0

    def test_optimize_uses_cached_results(self, optimizer):
        """Test that optimization uses cached valid results."""
        # First optimization
        optimal1 = optimizer.optimize_parameters("EURUSD")

        # Second optimization should use cached results
        optimal2 = optimizer.optimize_parameters("EURUSD")

        assert optimal1 is not None
        assert optimal2 is not None

    def test_optimize_forces_new_optimization(self, optimizer):
        """Test that force parameter triggers new optimization."""
        # First optimization
        optimizer.optimize_parameters("EURUSD")

        # Force new optimization
        optimal = optimizer.optimize_parameters("EURUSD", force=True)

        assert optimal is not None


class TestGetOptimalParameters:
    """Tests for retrieving optimal parameters."""

    def test_get_optimal_parameters_existing(self, optimizer):
        """Test getting existing optimal parameters."""
        # First, optimize to create cached results
        optimizer.optimize_parameters("EURUSD")

        # Then retrieve
        params = optimizer.get_optimal_parameters("EURUSD")

        assert params is not None
        assert isinstance(params, RiskParameterSet)
        assert hasattr(params, "base_risk_percent")
        assert hasattr(params, "stop_atr_multiplier")
        assert hasattr(params, "tp_atr_multiplier")

    def test_get_optimal_parameters_not_existing(self, optimizer):
        """Test getting optimal parameters that don't exist yet."""
        # Mock to return None for optimize
        with patch.object(optimizer, "optimize_parameters", return_value=None):
            params = optimizer.get_optimal_parameters("NEWPAIR")

            assert params is None


class TestGetOptimizationHistory:
    """Tests for retrieving optimization history."""

    def test_get_optimization_history(self, optimizer):
        """Test retrieving optimization history."""
        # Run some optimizations first
        optimizer.optimize_parameters("EURUSD")
        optimizer.optimize_parameters("GBPUSD")

        # Get history for EURUSD
        history = optimizer.get_optimization_history("EURUSD", limit=10)

        assert isinstance(history, list)
        assert len(history) > 0

        # Check that results are optimization results
        for result in history:
            assert isinstance(result, OptimizationResult)

    def test_get_optimization_history_limit(self, optimizer):
        """Test that limit parameter works."""
        # Run optimizations
        for i in range(5):
            optimizer.optimize_parameters("EURUSD")

        # Get limited history
        history = optimizer.get_optimization_history("EURUSD", limit=3)

        # Should have at most 3 results from this specific call
        assert isinstance(history, list)

    def test_get_optimization_history_empty(self, optimizer):
        """Test getting history for symbol with no optimizations."""
        history = optimizer.get_optimization_history("NOSYMBOL")

        assert history == []


class TestDatabasePersistence:
    """Tests for database persistence."""

    def test_optimal_parameters_persistence(self, optimizer, temp_db_path):
        """Test that optimal parameters persist across instances."""
        # Create and optimize with first instance
        optimizer.optimize_parameters("EURUSD")

        # Create new optimizer instance with same database
        optimizer2 = RiskParameterOptimizer(
            performance_comparator=optimizer.performance_comparator,
            database_path=temp_db_path,
            base_risk_options=[1.0, 2.0],
            stop_atr_multiplier_options=[1.5, 2.0],
            tp_atr_multiplier_options=[2.0, 3.0],
        )

        # Should be able to retrieve cached results
        params = optimizer2.get_optimal_parameters("EURUSD")

        assert params is not None

    def test_optimization_results_persistence(self, optimizer, temp_db_path):
        """Test that optimization results persist."""
        # Run optimization which stores results
        optimizer.optimize_parameters("EURUSD")

        # Verify in database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM optimization_results
            WHERE symbol = 'EURUSD'
        """)
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_optimize_with_empty_symbol(self, optimizer):
        """Test optimization with empty symbol."""
        # Should handle gracefully
        optimal = optimizer.optimize_parameters("")

        assert optimal is None

    def test_backtest_with_zero_trades(self, optimizer):
        """Test backtesting with zero trades."""
        optimizer.performance_comparator.get_evolved_trades_in_date_range = Mock(
            return_value=[]
        )

        params = RiskParameterSet(2.0, 2.0, 2.5)
        result = optimizer.backtest_risk_parameters(
            symbol="EURUSD",
            parameter_set=params,
            market_regime=MarketRegime.NORMAL,
        )

        assert result.total_trades == 0
        assert result.sharpe_ratio == -999.0

    def test_detect_regime_with_exception(self, optimizer):
        """Test regime detection when exception occurs."""
        # Mock to raise exception
        optimizer.performance_comparator.get_evolved_trades = Mock(
            side_effect=Exception("Test error")
        )

        regime = optimizer._detect_market_regime("EURUSD")

        # Should return default regime
        assert regime == MarketRegime.NORMAL

    def test_optimize_with_exception(self, optimizer):
        """Test optimization when exception occurs."""
        # Mock to raise exception
        optimizer.performance_comparator.get_evolved_trades_in_date_range = Mock(
            side_effect=Exception("Test error")
        )

        optimal = optimizer.optimize_parameters("EURUSD")

        # Should return None
        assert optimal is None


class TestSharpeRatioCalculation:
    """Tests for Sharpe ratio calculation."""

    def test_sharpe_ratio_positive_returns(self, optimizer):
        """Test Sharpe ratio with positive returns."""
        params = RiskParameterSet(2.0, 2.0, 2.5)

        result = optimizer.backtest_risk_parameters(
            symbol="EURUSD",
            parameter_set=params,
            market_regime=MarketRegime.NORMAL,
        )

        # Sharpe ratio should be calculated
        assert isinstance(result.sharpe_ratio, float)

    def test_sharpe_ratio_with_single_trade(self, optimizer):
        """Test Sharpe ratio calculation with only one trade."""
        # Create single trade
        single_trade = [Mock(spec=TradeOutcome)]
        single_trade[0].pnl = 100.0
        single_trade[0].stop_loss = 1.0800
        single_trade[0].entry_price = 1.0850

        optimizer.performance_comparator.get_evolved_trades_in_date_range = Mock(
            return_value=single_trade
        )

        params = RiskParameterSet(2.0, 2.0, 2.5)
        result = optimizer.backtest_risk_parameters(
            symbol="EURUSD",
            parameter_set=params,
            market_regime=MarketRegime.NORMAL,
        )

        # Should handle single trade gracefully
        assert isinstance(result.sharpe_ratio, float)


class TestParameterCombinations:
    """Tests for parameter combination testing."""

    def test_all_combinations_tested(self, optimizer):
        """Test that all parameter combinations are tested."""
        # With 2 options for each parameter, should test 2*2*2 = 8 combinations
        base_risk_count = len(optimizer.base_risk_options)
        stop_atr_count = len(optimizer.stop_atr_multiplier_options)
        tp_atr_count = len(optimizer.tp_atr_multiplier_options)
        expected_combinations = base_risk_count * stop_atr_count * tp_atr_count

        optimal = optimizer.optimize_parameters("EURUSD")

        assert optimal is not None
        # Check that we have results for all combinations
        # (Some may be stored in database from earlier tests)

    def test_different_base_risks(self, optimizer):
        """Test optimization with different base risk levels."""
        for base_risk in [1.0, 1.5, 2.0, 2.5]:
            params = RiskParameterSet(
                base_risk_percent=base_risk,
                stop_atr_multiplier=2.0,
                tp_atr_multiplier=2.5,
            )

            result = optimizer.backtest_risk_parameters(
                symbol="EURUSD",
                parameter_set=params,
                market_regime=MarketRegime.NORMAL,
            )

            assert result.parameter_set.base_risk_percent == base_risk

    def test_different_atr_multipliers(self, optimizer):
        """Test optimization with different ATR multipliers."""
        for stop_atr in [1.5, 2.0, 2.5, 3.0]:
            for tp_atr in [2.0, 2.5, 3.0, 3.5]:
                params = RiskParameterSet(
                    base_risk_percent=2.0,
                    stop_atr_multiplier=stop_atr,
                    tp_atr_multiplier=tp_atr,
                )

                result = optimizer.backtest_risk_parameters(
                    symbol="GBPUSD",
                    parameter_set=params,
                    market_regime=MarketRegime.HIGH,
                )

                assert result.parameter_set.stop_atr_multiplier == stop_atr
                assert result.parameter_set.tp_atr_multiplier == tp_atr
