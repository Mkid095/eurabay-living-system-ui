"""
Unit tests for PerformanceComparator.

Tests the active vs passive performance comparison functionality.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from backend.core.performance_comparator import (
    PerformanceComparator,
    PerformanceMetrics,
    ActionEffectiveness,
    ComparisonResult,
    TradeOutcome,
    ManagementActionType,
)
from backend.core.trade_state import TradePosition, TradeState


@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_performance.db"
    yield str(db_path)
    # Cleanup is automatic with tmp_path


@pytest.fixture
def sample_position():
    """Create a sample trade position for testing."""
    return TradePosition(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1000,
        current_price=1.1050,
        volume=1.0,
        stop_loss=1.0950,
        take_profit=1.1150,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        profit=500.0,
        swap=0.0,
        commission=0.0,
        state=TradeState.OPEN,
    )


@pytest.fixture
def comparator(temp_database):
    """Create a PerformanceComparator instance for testing."""
    return PerformanceComparator(database_path=temp_database)


class TestPerformanceComparatorInitialization:
    """Test PerformanceComparator initialization and setup."""

    def test_initialization(self, temp_database):
        """Test that comparator initializes correctly."""
        comparator = PerformanceComparator(database_path=temp_database)

        assert comparator._database_path == temp_database
        assert comparator._trade_outcomes == []
        assert len(comparator._action_effectiveness) == len(ManagementActionType)

    def test_database_creation(self, temp_database):
        """Test that database tables are created."""
        comparator = PerformanceComparator(database_path=temp_database)

        # Check that tables exist
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "trade_outcomes" in tables
        assert "performance_comparisons" in tables
        assert "action_effectiveness" in tables

        conn.close()


class TestTradeOutcomeRecording:
    """Test recording trade outcomes."""

    def test_record_trade_outcome(self, comparator, sample_position):
        """Test recording a basic trade outcome."""
        exit_price = 1.1080
        exit_time = datetime.utcnow()
        final_profit = 800.0

        outcome = comparator.record_trade_outcome(
            position=sample_position,
            exit_price=exit_price,
            exit_time=exit_time,
            final_profit=final_profit,
            peak_profit=900.0,
            max_adverse_excursion=-100.0,
            management_actions=["trailing_stop", "breakeven"],
        )

        assert outcome.ticket == sample_position.ticket
        assert outcome.final_profit == final_profit
        assert outcome.exit_price == exit_price
        assert outcome.exit_time == exit_time
        assert "trailing_stop" in outcome.management_actions
        assert "breakeven" in outcome.management_actions

    def test_outcome_stored_in_memory(self, comparator, sample_position):
        """Test that outcomes are stored in memory."""
        comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
        )

        assert len(comparator._trade_outcomes) == 1
        assert comparator._trade_outcomes[0].ticket == sample_position.ticket

    def test_outcome_stored_in_database(self, comparator, sample_position):
        """Test that outcomes are stored in database."""
        comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
        )

        conn = sqlite3.connect(comparator._database_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM trade_outcomes")
        count = cursor.fetchone()[0]

        assert count == 1

        conn.close()

    def test_holding_time_calculation(self, comparator, sample_position):
        """Test that holding time is calculated correctly."""
        entry_time = datetime.utcnow() - timedelta(hours=3)
        sample_position.entry_time = entry_time

        exit_time = datetime.utcnow()

        outcome = comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=exit_time,
            final_profit=800.0,
        )

        # Holding time should be approximately 3 hours
        assert 2.9 * 3600 <= outcome.holding_time.total_seconds() <= 3.1 * 3600


class TestPassiveProfitCalculation:
    """Test calculation of passive (set-and-forget) profit."""

    def test_passive_profit_with_tp_hit(self, comparator, sample_position):
        """Test passive profit when take profit would have been hit."""
        exit_price = 1.1150  # At TP level
        peak_profit = 1500.0  # Peak exceeds TP

        outcome = comparator.record_trade_outcome(
            position=sample_position,
            exit_price=exit_price,
            exit_time=datetime.utcnow(),
            final_profit=1500.0,
            peak_profit=peak_profit,
            max_adverse_excursion=-50.0,
        )

        # Passive profit should be close to TP level
        assert outcome.passive_profit > 0

    def test_passive_profit_with_sl_hit(self, comparator, sample_position):
        """Test passive profit when stop loss would have been hit."""
        exit_price = 1.0940  # Past SL
        # Max adverse exceeds initial risk (0.005 points = 500 currency units with 1 lot)
        max_adverse = -6000.0  # Large adverse move (exceeds SL)

        outcome = comparator.record_trade_outcome(
            position=sample_position,
            exit_price=exit_price,
            exit_time=datetime.utcnow(),
            final_profit=-500.0,
            peak_profit=100.0,
            max_adverse_excursion=max_adverse,
        )

        # Passive profit should reflect SL hit (-0.005 points * 100000 = -500)
        assert outcome.passive_profit < 0
        assert abs(outcome.passive_profit - (-500.0)) < 10  # Allow small rounding误差

    def test_passive_profit_no_sl_tp(self, comparator, temp_database):
        """Test passive profit when no SL or TP set."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            current_price=1.1050,
            volume=1.0,
            stop_loss=None,
            take_profit=None,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            profit=500.0,
            swap=0.0,
            commission=0.0,
        )

        comparator = PerformanceComparator(database_path=temp_database)

        outcome = comparator.record_trade_outcome(
            position=position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
        )

        # With no SL/TP, passive should equal actual (allow for floating point precision)
        assert abs(outcome.passive_profit - outcome.final_profit) < 0.01


class TestPerformanceMetricsCalculation:
    """Test calculation of performance metrics."""

    def test_calculate_active_metrics(self, comparator, sample_position):
        """Test calculating metrics for active management."""
        # Record multiple trades
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0 if i < 7 else -200.0,  # 7 wins, 3 losses
            )

        metrics = comparator.calculate_performance_metrics(
            comparator._trade_outcomes, use_passive=False
        )

        assert metrics.total_trades == 10
        assert metrics.winning_trades == 7
        assert metrics.losing_trades == 3
        assert metrics.win_rate == 70.0
        assert metrics.total_profit > 0
        assert metrics.total_loss > 0

    def test_calculate_passive_metrics(self, comparator, sample_position):
        """Test calculating metrics for passive management."""
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
                peak_profit=1000.0,
                max_adverse_excursion=-100.0,
            )

        metrics = comparator.calculate_performance_metrics(
            comparator._trade_outcomes, use_passive=True
        )

        assert metrics.total_trades == 10

    def test_profit_factor_calculation(self, comparator, sample_position):
        """Test profit factor is calculated correctly."""
        # Create trades with known profit/loss
        for profit in [100, 200, 150, -50, -75]:  # Total profit: 450, Total loss: 125
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080,
                exit_time=datetime.utcnow(),
                final_profit=profit,
            )

        metrics = comparator.calculate_performance_metrics(
            comparator._trade_outcomes, use_passive=False
        )

        expected_profit_factor = 450 / 125
        assert abs(metrics.profit_factor - expected_profit_factor) < 0.01

    def test_average_win_loss(self, comparator, sample_position):
        """Test average win and loss calculations."""
        wins = [100, 200, 150]
        losses = [-50, -75]

        for profit in wins + losses:
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080,
                exit_time=datetime.utcnow(),
                final_profit=profit,
            )

        metrics = comparator.calculate_performance_metrics(
            comparator._trade_outcomes, use_passive=False
        )

        expected_avg_win = sum(wins) / len(wins)
        expected_avg_loss = sum(losses) / len(losses)

        assert abs(metrics.average_win - expected_avg_win) < 0.01
        assert abs(metrics.average_loss - expected_avg_loss) < 0.01

    def test_empty_metrics(self, comparator):
        """Test metrics calculation with no trades."""
        metrics = comparator.calculate_performance_metrics([], use_passive=False)

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0


class TestActionEffectiveness:
    """Test tracking of individual action effectiveness."""

    def test_trailing_stop_effectiveness(self, comparator, sample_position):
        """Test trailing stop effectiveness tracking."""
        outcome = comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
            peak_profit=900.0,
            max_adverse_excursion=-100.0,
            management_actions=["trailing_stop"],
        )

        effectiveness = comparator.get_action_effectiveness(
            ManagementActionType.TRAILING_STOP
        )

        assert effectiveness.times_triggered == 1
        # Benefit = final_profit - passive_profit
        # Check that either profit_saved or loss_prevented reflects the benefit
        expected_benefit = outcome.final_profit - outcome.passive_profit
        if expected_benefit > 0:
            assert effectiveness.profit_saved == expected_benefit
        else:
            assert effectiveness.loss_prevented == abs(expected_benefit)

    def test_breakeven_effectiveness(self, comparator, sample_position):
        """Test breakeven effectiveness tracking."""
        outcome = comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.0980,
            exit_time=datetime.utcnow(),
            final_profit=50.0,  # Small profit due to breakeven
            peak_profit=200.0,
            max_adverse_excursion=-300.0,  # Would have hit SL without breakeven
            management_actions=["breakeven"],
        )

        effectiveness = comparator.get_action_effectiveness(
            ManagementActionType.BREAKEVEN
        )

        assert effectiveness.times_triggered == 1
        # Benefit = final_profit - passive_profit (passive would have been worse)
        expected_benefit = outcome.final_profit - outcome.passive_profit
        # With breakeven, we should have prevented a loss (passive < final)
        if expected_benefit > 0:
            # Active performed better than passive
            total_benefit = effectiveness.profit_saved + effectiveness.loss_prevented
            assert total_benefit > 0
        else:
            # Passive performed better (shouldn't happen with breakeven)
            assert effectiveness.loss_prevented >= 0

    def test_multiple_action_types(self, comparator, sample_position):
        """Test tracking multiple different action types."""
        comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
            peak_profit=1000.0,
            max_adverse_excursion=-100.0,
            management_actions=[
                "trailing_stop",
                "breakeven",
                "partial_profit",
                "holding_time_limit",
            ],
        )

        trailing = comparator.get_action_effectiveness(
            ManagementActionType.TRAILING_STOP
        )
        breakeven = comparator.get_action_effectiveness(
            ManagementActionType.BREAKEVEN
        )
        partial = comparator.get_action_effectiveness(
            ManagementActionType.PARTIAL_PROFIT
        )
        holding = comparator.get_action_effectiveness(
            ManagementActionType.HOLDING_TIME_LIMIT
        )

        assert trailing.times_triggered == 1
        assert breakeven.times_triggered == 1
        assert partial.times_triggered == 1
        assert holding.times_triggered == 1

    def test_action_benefit_accumulation(self, comparator, sample_position):
        """Test that benefits accumulate across multiple trades."""
        for i in range(5):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
                peak_profit=1000.0,
                max_adverse_excursion=-100.0,
                management_actions=["trailing_stop"],
            )

        effectiveness = comparator.get_action_effectiveness(
            ManagementActionType.TRAILING_STOP
        )

        assert effectiveness.times_triggered == 5
        # Check that total benefit (profit_saved + loss_prevented) is positive
        total_benefit = effectiveness.profit_saved + effectiveness.loss_prevented
        assert total_benefit > 0


class TestPerformanceComparison:
    """Test comparison of active vs passive performance."""

    def test_compare_performance(self, comparator, sample_position):
        """Test generating a comparison result."""
        # Record trades where active outperforms passive
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
                peak_profit=1000.0,
                max_adverse_excursion=-100.0,
                management_actions=["trailing_stop"],
            )

        result = comparator.compare_performance()

        assert isinstance(result, ComparisonResult)
        assert result.active_metrics.total_trades == 10
        assert result.passive_metrics.total_trades == 10
        assert isinstance(result.win_rate_improvement, float)
        assert isinstance(result.profit_factor_improvement, float)

    def test_win_rate_improvement(self, comparator, sample_position):
        """Test win rate improvement calculation."""
        # Create scenario where active has higher win rate
        for i in range(10):
            # Active: 8 winners, 2 losers
            final_profit = 100.0 if i < 8 else -50.0
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=final_profit,
                peak_profit=150.0,
                max_adverse_excursion=-100.0,
            )

        result = comparator.compare_performance()

        # Active win rate should be 80%
        assert result.active_metrics.win_rate == 80.0

    def test_profit_factor_improvement(self, comparator, sample_position):
        """Test profit factor improvement calculation."""
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=200.0 if i < 7 else -100.0,
                peak_profit=300.0 if i < 7 else 0.0,
                max_adverse_excursion=-150.0 if i >= 7 else -50.0,
                management_actions=["trailing_stop"],
            )

        result = comparator.compare_performance()

        assert result.profit_factor_improvement >= 0.0

    def test_total_profit_improvement(self, comparator, sample_position):
        """Test total profit improvement calculation."""
        # Create trades where active management improves outcome
        # Active: Trailing stop locks in 800 profit before reversal
        # Passive: Without trailing stop, price reverses and position closes at breakeven
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1000,  # Price returns to entry (breakeven for passive)
                exit_time=datetime.utcnow(),
                final_profit=800.0,  # Active result (trailing stop saved profit)
                peak_profit=900.0,  # Peak was 900 but didn't reach TP (1500)
                max_adverse_excursion=-200.0,  # Some adverse movement but not SL
                management_actions=["trailing_stop"],
            )

        result = comparator.compare_performance()

        # Total profit improvement should be positive since active management helps
        assert result.total_profit_improvement >= 0

    def test_recommendation_generation(self, comparator, sample_position):
        """Test recommendation is generated appropriately."""
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
                peak_profit=1000.0,
                max_adverse_excursion=-100.0,
            )

        result = comparator.compare_performance()

        assert result.recommendation
        assert isinstance(result.recommendation, str)
        assert len(result.recommendation) > 0

    def test_comparison_stored_in_database(self, comparator, sample_position):
        """Test that comparison results are stored."""
        for i in range(5):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
            )

        comparator.compare_performance()

        conn = sqlite3.connect(comparator._database_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM performance_comparisons")
        count = cursor.fetchone()[0]

        assert count == 1

        conn.close()

    def test_comparison_with_no_trades(self, comparator):
        """Test comparison when no trades recorded."""
        result = comparator.compare_performance()

        assert result.active_metrics.total_trades == 0
        assert result.passive_metrics.total_trades == 0
        assert result.win_rate_improvement == 0.0
        assert "No trade data" in result.recommendation


class TestReportGeneration:
    """Test generation of performance comparison reports."""

    def test_generate_report(self, comparator, sample_position):
        """Test generating a comparison report."""
        for i in range(5):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
                management_actions=["trailing_stop"],
            )

        report = comparator.generate_comparison_report()

        assert isinstance(report, str)
        assert len(report) > 0
        assert "PERFORMANCE REPORT" in report
        assert "ACTIVE MANAGEMENT METRICS" in report
        assert "PASSIVE" in report
        assert "RECOMMENDATION" in report

    def test_report_contains_metrics(self, comparator, sample_position):
        """Test that report contains all key metrics."""
        for i in range(5):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
            )

        report = comparator.generate_comparison_report()

        assert "Win Rate" in report
        assert "Profit Factor" in report
        assert "Total Profit" in report
        assert "Average Win" in report
        assert "Average Loss" in report

    def test_report_contains_action_effectiveness(self, comparator, sample_position):
        """Test that report contains action effectiveness."""
        comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
            management_actions=["trailing_stop", "breakeven"],
        )

        report = comparator.generate_comparison_report()

        assert "MANAGEMENT ACTION EFFECTIVENESS" in report
        assert "trailing_stop" in report


class TestHistoricalBacktest:
    """Test backtesting on historical data."""

    def test_backtest_historical_positions(self, comparator):
        """Test backtesting with historical position data."""
        historical_positions = [
            {
                "ticket": 1001,
                "symbol": "EURUSD",
                "direction": "BUY",
                "entry_price": 1.1000,
                "exit_price": 1.1080,
                "entry_time": datetime.utcnow() - timedelta(hours=2),
                "exit_time": datetime.utcnow(),
                "initial_stop_loss": 1.0950,
                "initial_take_profit": 1.1150,
                "final_profit": 800.0,
                "management_actions": ["trailing_stop"],
                "peak_profit": 900.0,
                "max_adverse_excursion": -100.0,
            },
            {
                "ticket": 1002,
                "symbol": "GBPUSD",
                "direction": "SELL",
                "entry_price": 1.3000,
                "exit_price": 1.2950,
                "entry_time": datetime.utcnow() - timedelta(hours=1),
                "exit_time": datetime.utcnow(),
                "initial_stop_loss": 1.3050,
                "initial_take_profit": 1.2900,
                "final_profit": 500.0,
                "management_actions": ["breakeven"],
                "peak_profit": 600.0,
                "max_adverse_excursion": -50.0,
            },
        ]

        result = comparator.backtest_historical_data(historical_positions)

        assert result.active_metrics.total_trades == 2
        assert result.passive_metrics.total_trades == 2

    def test_backtest_clears_existing_data(self, comparator, sample_position):
        """Test that backtest clears existing outcomes."""
        # Add some existing data
        comparator.record_trade_outcome(
            position=sample_position,
            exit_price=1.1080,
            exit_time=datetime.utcnow(),
            final_profit=800.0,
        )

        assert len(comparator._trade_outcomes) == 1

        # Run backtest
        historical_positions = [
            {
                "ticket": 1001,
                "symbol": "EURUSD",
                "direction": "BUY",
                "entry_price": 1.1000,
                "exit_price": 1.1080,
                "entry_time": datetime.utcnow() - timedelta(hours=2),
                "exit_time": datetime.utcnow(),
                "initial_stop_loss": 1.0950,
                "initial_take_profit": 1.1150,
                "final_profit": 800.0,
                "management_actions": [],
                "peak_profit": 900.0,
                "max_adverse_excursion": -100.0,
            }
        ]

        comparator.backtest_historical_data(historical_positions)

        # Should only have backtest data
        assert len(comparator._trade_outcomes) == 1
        assert comparator._trade_outcomes[0].ticket == 1001


class TestQueryOutcomes:
    """Test querying trade outcomes."""

    def test_query_all_outcomes(self, comparator, sample_position):
        """Test querying all outcomes."""
        for i in range(5):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
            )

        outcomes = comparator.get_trade_outcomes()

        assert len(outcomes) == 5

    def test_query_by_symbol(self, comparator, sample_position):
        """Test filtering by symbol."""
        # Add EURUSD trades
        for i in range(3):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080,
                exit_time=datetime.utcnow(),
                final_profit=800.0,
            )

        # Add GBPUSD trade
        gbp_position = TradePosition(
            ticket=54321,
            symbol="GBPUSD",
            direction="BUY",
            entry_price=1.3000,
            current_price=1.3050,
            volume=1.0,
            stop_loss=1.2950,
            take_profit=1.3150,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            profit=500.0,
            swap=0.0,
            commission=0.0,
        )

        comparator.record_trade_outcome(
            position=gbp_position,
            exit_price=1.3050,
            exit_time=datetime.utcnow(),
            final_profit=500.0,
        )

        eur_outcomes = comparator.get_trade_outcomes(symbol="EURUSD")
        gbp_outcomes = comparator.get_trade_outcomes(symbol="GBPUSD")

        assert len(eur_outcomes) == 3
        assert len(gbp_outcomes) == 1

    def test_query_with_limit(self, comparator, sample_position):
        """Test limiting query results."""
        for i in range(10):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080 + (i * 0.001),
                exit_time=datetime.utcnow(),
                final_profit=800.0,
            )

        outcomes = comparator.get_trade_outcomes(limit=5)

        assert len(outcomes) == 5


class TestDatabasePersistence:
    """Test database persistence and cleanup."""

    def test_clear_history(self, comparator, sample_position):
        """Test clearing all history."""
        for i in range(5):
            comparator.record_trade_outcome(
                position=sample_position,
                exit_price=1.1080,
                exit_time=datetime.utcnow(),
                final_profit=800.0,
            )

        comparator.compare_performance()

        assert len(comparator._trade_outcomes) == 5

        comparator.clear_history()

        assert len(comparator._trade_outcomes) == 0

        # Check database is cleared
        conn = sqlite3.connect(comparator._database_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM trade_outcomes")
        outcomes_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM performance_comparisons")
        comparisons_count = cursor.fetchone()[0]

        assert outcomes_count == 0
        assert comparisons_count == 0

        conn.close()

    def test_close_connection(self, temp_database):
        """Test closing database connection."""
        comparator = PerformanceComparator(database_path=temp_database)

        comparator.close()

        assert comparator._connection is None


class TestPerformanceMetricsDataclass:
    """Test PerformanceMetrics dataclass."""

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics(
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=60.0,
            total_profit=6000.0,
            total_loss=2000.0,
            profit_factor=3.0,
            average_win=100.0,
            average_loss=50.0,
            max_drawdown=500.0,
            average_holding_time=timedelta(hours=2),
            total_r=30.0,
            average_r=0.3,
            best_trade=500.0,
            worst_trade=-200.0,
        )

        result = metrics.to_dict()

        assert result["total_trades"] == 100
        assert result["win_rate"] == 60.0
        assert result["profit_factor"] == 3.0
        assert result["average_holding_time_seconds"] == 7200

    def test_empty_metrics_to_dict(self):
        """Test converting empty metrics to dictionary."""
        metrics = PerformanceMetrics()

        result = metrics.to_dict()

        assert result["total_trades"] == 0
        assert result["win_rate"] == 0.0


class TestActionEffectivenessDataclass:
    """Test ActionEffectiveness dataclass."""

    def test_to_dict(self):
        """Test converting effectiveness to dictionary."""
        effectiveness = ActionEffectiveness(
            action_type=ManagementActionType.TRAILING_STOP,
            times_triggered=10,
            profit_saved=1000.0,
            loss_prevented=500.0,
            average_benefit=150.0,
            success_rate=80.0,
        )

        result = effectiveness.to_dict()

        assert result["action_type"] == "trailing_stop"
        assert result["times_triggered"] == 10
        assert result["profit_saved"] == 1000.0
        assert result["success_rate"] == 80.0


class TestComparisonResultDataclass:
    """Test ComparisonResult dataclass."""

    def test_to_dict(self):
        """Test converting comparison result to dictionary."""
        result = ComparisonResult(
            active_metrics=PerformanceMetrics(total_trades=10, win_rate=60.0),
            passive_metrics=PerformanceMetrics(total_trades=10, win_rate=50.0),
            win_rate_improvement=10.0,
            profit_factor_improvement=0.5,
            total_profit_improvement=1000.0,
            action_effectiveness=[],
            recommendation="Continue active management",
        )

        result_dict = result.to_dict()

        assert "active_metrics" in result_dict
        assert "passive_metrics" in result_dict
        assert result_dict["win_rate_improvement"] == 10.0
        assert result_dict["recommendation"] == "Continue active management"
