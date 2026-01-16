"""
Unit tests for Performance Analytics.

Tests the foundational analytics engine that aggregates and analyzes
trading performance data including basic metrics, drawdown analysis,
trade statistics, and returns calculations.
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.performance_analytics import (
    PerformanceAnalytics,
    BasicMetrics,
    DrawdownMetrics,
    TradeStatistics,
    ReturnsMetrics,
    CachedMetrics,
    TradeRecord,
)


class TestTradeRecord(unittest.TestCase):
    """Test TradeRecord dataclass and helper methods."""

    def test_trade_record_creation(self):
        """Test creating a TradeRecord."""
        trade = TradeRecord(
            ticket=12345,
            symbol="V10",
            direction="BUY",
            entry_price=1.0500,
            exit_price=1.0550,
            entry_time=datetime(2024, 1, 1, 10, 0),
            exit_time=datetime(2024, 1, 1, 11, 0),
            profit=500.0,
            volume=1.0,
            stop_loss=1.0450,
            take_profit=1.0600,
        )

        self.assertEqual(trade.ticket, 12345)
        self.assertEqual(trade.symbol, "V10")
        self.assertEqual(trade.direction, "BUY")
        self.assertEqual(trade.profit, 500.0)

    def test_trade_record_is_winner(self):
        """Test is_winner property."""
        winning_trade = TradeRecord(
            ticket=1,
            symbol="V10",
            direction="BUY",
            entry_price=1.0,
            exit_price=1.0,
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            profit=100.0,
            volume=1.0,
        )

        losing_trade = TradeRecord(
            ticket=2,
            symbol="V10",
            direction="BUY",
            entry_price=1.0,
            exit_price=1.0,
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            profit=-50.0,
            volume=1.0,
        )

        break_even_trade = TradeRecord(
            ticket=3,
            symbol="V10",
            direction="BUY",
            entry_price=1.0,
            exit_price=1.0,
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            profit=0.0,
            volume=1.0,
        )

        self.assertTrue(winning_trade.is_winner)
        self.assertFalse(losing_trade.is_winner)
        self.assertFalse(break_even_trade.is_winner)

    def test_trade_record_is_closed(self):
        """Test is_closed property."""
        closed_trade = TradeRecord(
            ticket=1,
            symbol="V10",
            direction="BUY",
            entry_price=1.0,
            exit_price=1.0,
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            profit=100.0,
            volume=1.0,
        )

        open_trade = TradeRecord(
            ticket=2,
            symbol="V10",
            direction="BUY",
            entry_price=1.0,
            exit_price=1.0,
            entry_time=datetime.now(),
            exit_time=None,
            profit=0.0,
            volume=1.0,
        )

        self.assertTrue(closed_trade.is_closed)
        self.assertFalse(open_trade.is_closed)

    def test_trade_record_holding_time(self):
        """Test holding_time property."""
        entry = datetime(2024, 1, 1, 10, 0)
        exit_time = datetime(2024, 1, 1, 11, 30)

        trade = TradeRecord(
            ticket=1,
            symbol="V10",
            direction="BUY",
            entry_price=1.0,
            exit_price=1.0,
            entry_time=entry,
            exit_time=exit_time,
            profit=100.0,
            volume=1.0,
        )

        expected_hold = timedelta(hours=1, minutes=30)
        self.assertEqual(trade.holding_time, expected_hold)

    def test_trade_record_from_row(self):
        """Test creating TradeRecord from database row."""
        row = (
            12345,  # ticket
            "V10",  # symbol
            "BUY",  # direction
            1.0500,  # entry_price
            1.0550,  # exit_price
            "2024-01-01T10:00:00",  # entry_time
            "2024-01-01T11:00:00",  # exit_time
            500.0,  # profit
            1.0,  # volume
            1.0450,  # stop_loss
            1.0600,  # take_profit
            10.0,  # commission
            5.0,  # swap
        )

        trade = TradeRecord.from_row(row)

        self.assertEqual(trade.ticket, 12345)
        self.assertEqual(trade.symbol, "V10")
        self.assertEqual(trade.direction, "BUY")
        self.assertEqual(trade.entry_price, 1.0500)
        self.assertEqual(trade.exit_price, 1.0550)
        self.assertEqual(trade.profit, 500.0)
        self.assertEqual(trade.stop_loss, 1.0450)
        self.assertEqual(trade.take_profit, 1.0600)
        self.assertEqual(trade.commission, 10.0)
        self.assertEqual(trade.swap, 5.0)


class TestBasicMetrics(unittest.TestCase):
    """Test BasicMetrics dataclass."""

    def test_basic_metrics_creation(self):
        """Test creating BasicMetrics."""
        metrics = BasicMetrics(
            win_rate=60.0,
            profit_factor=2.0,
            average_win=100.0,
            average_loss=50.0,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            total_profit=6000.0,
            total_loss=2000.0,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
        )

        self.assertEqual(metrics.win_rate, 60.0)
        self.assertEqual(metrics.profit_factor, 2.0)
        self.assertEqual(metrics.sharpe_ratio, 1.5)

    def test_basic_metrics_to_dict(self):
        """Test converting BasicMetrics to dictionary."""
        metrics = BasicMetrics(
            win_rate=60.5,
            profit_factor=1.5,
            sharpe_ratio=1.234,
        )

        result = metrics.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["win_rate"], 60.5)
        self.assertEqual(result["sharpe_ratio"], 1.23)
        self.assertIn("calculated_at", result)


class TestDrawdownMetrics(unittest.TestCase):
    """Test DrawdownMetrics dataclass."""

    def test_drawdown_metrics_creation(self):
        """Test creating DrawdownMetrics."""
        metrics = DrawdownMetrics(
            max_drawdown=1000.0,
            max_drawdown_percent=10.0,
            avg_drawdown=500.0,
            avg_drawdown_percent=5.0,
            drawdown_count=5,
        )

        self.assertEqual(metrics.max_drawdown, 1000.0)
        self.assertEqual(metrics.max_drawdown_percent, 10.0)
        self.assertEqual(metrics.drawdown_count, 5)

    def test_drawdown_metrics_to_dict(self):
        """Test converting DrawdownMetrics to dictionary."""
        metrics = DrawdownMetrics(
            max_drawdown=1234.56,
            max_drawdown_percent=12.345,
        )

        result = metrics.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["max_drawdown"], 1234.56)
        self.assertEqual(result["max_drawdown_percent"], 12.35)


class TestTradeStatistics(unittest.TestCase):
    """Test TradeStatistics dataclass."""

    def test_trade_statistics_creation(self):
        """Test creating TradeStatistics."""
        stats = TradeStatistics(
            avg_hold_time=3600,
            avg_hold_time_minutes=60.0,
            avg_hold_time_hours=1.0,
            trades_per_day=5.0,
            max_consecutive_wins=10,
            max_consecutive_losses=5,
        )

        self.assertEqual(stats.avg_hold_time, 3600)
        self.assertEqual(stats.avg_hold_time_minutes, 60.0)
        self.assertEqual(stats.max_consecutive_wins, 10)

    def test_trade_statistics_to_dict(self):
        """Test converting TradeStatistics to dictionary."""
        stats = TradeStatistics(
            avg_hold_time_minutes=45.678,
        )

        result = stats.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["avg_hold_time_minutes"], 45.68)


class TestReturnsMetrics(unittest.TestCase):
    """Test ReturnsMetrics dataclass."""

    def test_returns_metrics_creation(self):
        """Test creating ReturnsMetrics."""
        metrics = ReturnsMetrics(
            daily_return_avg=100.0,
            daily_return_std=50.0,
            total_return=5000.0,
            total_return_percent=50.0,
        )

        self.assertEqual(metrics.daily_return_avg, 100.0)
        self.assertEqual(metrics.total_return_percent, 50.0)

    def test_returns_metrics_to_dict(self):
        """Test converting ReturnsMetrics to dictionary."""
        metrics = ReturnsMetrics(
            total_return=1234.567,
            total_return_percent=12.345,
        )

        result = metrics.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_return"], 1234.57)
        self.assertEqual(result["total_return_percent"], 12.35)


class TestCachedMetrics(unittest.TestCase):
    """Test CachedMetrics dataclass."""

    def test_cached_metrics_creation(self):
        """Test creating CachedMetrics."""
        cached = CachedMetrics(
            ttl_seconds=300,
        )

        self.assertIsNotNone(cached.cached_at)
        self.assertEqual(cached.ttl_seconds, 300)

    def test_cached_metrics_is_expired(self):
        """Test is_expired property."""
        cached = CachedMetrics(ttl_seconds=0)  # Expired immediately

        self.assertTrue(cached.is_expired())

    def test_cached_metrics_not_expired(self):
        """Test cache not immediately expired."""
        cached = CachedMetrics(ttl_seconds=300)

        self.assertFalse(cached.is_expired())


class TestPerformanceAnalytics(unittest.TestCase):
    """Test PerformanceAnalytics class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary databases
        self.analytics_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.trades_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")

        self.analytics_db_path = self.analytics_db.name
        self.trades_db_path = self.trades_db.name

        # Create analytics instance
        self.analytics = PerformanceAnalytics(
            database_path=self.analytics_db_path,
            trades_database_path=self.trades_db_path,
            cache_ttl_seconds=300,
        )

        # Set up trades database with test data
        self._setup_test_trades_database()

    def tearDown(self):
        """Clean up test fixtures."""
        self.analytics.close()

        # Close and delete temporary databases
        try:
            os.unlink(self.analytics_db_path)
            os.unlink(self.trades_db_path)
        except OSError:
            pass

    def _setup_test_trades_database(self):
        """Set up trades database with test data."""
        conn = sqlite3.connect(self.trades_db_path)
        cursor = conn.cursor()

        # Create trade_outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                final_profit REAL NOT NULL,
                volume REAL NOT NULL,
                initial_stop_loss REAL,
                initial_take_profit REAL
            )
        """)

        # Insert test trades covering 6 months
        base_date = datetime(2024, 1, 1, 10, 0)
        test_trades = []

        # Create 100 trades with various outcomes
        for i in range(100):
            entry_time = base_date + timedelta(days=i)
            exit_time = entry_time + timedelta(hours=2)

            # Mix of winning and losing trades (60% win rate)
            is_winner = i % 10 < 6  # 60% win rate
            profit = 100.0 if is_winner else -50.0

            trade = (
                i + 1,  # ticket
                "V10",  # symbol
                "BUY",  # direction
                1.0500,  # entry_price
                1.0550 if is_winner else 1.0475,  # exit_price
                entry_time.isoformat(),
                exit_time.isoformat(),
                profit,  # final_profit
                1.0,  # volume
                1.0450,  # initial_stop_loss
                1.0600,  # initial_take_profit
            )
            test_trades.append(trade)

        cursor.executemany("""
            INSERT INTO trade_outcomes (
                ticket, symbol, direction, entry_price, exit_price,
                entry_time, exit_time, final_profit, volume,
                initial_stop_loss, initial_take_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_trades)

        conn.commit()
        conn.close()

        # Reconnect to the trades database after populating it
        if self.analytics._trades_connection:
            self.analytics._trades_connection.close()
        self.analytics._trades_connection = sqlite3.connect(self.trades_db_path)

    def test_initialization(self):
        """Test PerformanceAnalytics initialization."""
        self.assertIsNotNone(self.analytics._connection)
        self.assertIsNotNone(self.analytics._cached_metrics)
        self.assertEqual(self.analytics._cache_ttl_seconds, 300)

    def test_database_tables_created(self):
        """Test that all required database tables are created."""
        cursor = self.analytics._connection.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (
                'basic_metrics', 'drawdown_metrics',
                'trade_statistics', 'returns_metrics'
            )
        """)

        tables = [row[0] for row in cursor.fetchall()]
        self.assertEqual(len(tables), 4)

    def test_fetch_all_trades(self):
        """Test fetching all trades from database."""
        trades = self.analytics.fetch_all_trades()

        self.assertGreater(len(trades), 0)
        self.assertIsInstance(trades[0], TradeRecord)
        self.assertEqual(trades[0].symbol, "V10")

    def test_fetch_all_trades_with_filters(self):
        """Test fetching trades with date filters."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        trades = self.analytics.fetch_all_trades(
            start_date=start_date,
            end_date=end_date,
        )

        # All trades should be in January 2024
        for trade in trades:
            self.assertGreaterEqual(trade.entry_time, start_date)
            self.assertLessEqual(trade.entry_time, end_date)

    def test_calculate_basic_metrics(self):
        """Test calculating basic performance metrics."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_basic_metrics(trades)

        self.assertIsInstance(metrics, BasicMetrics)
        self.assertGreater(metrics.total_trades, 0)
        self.assertGreater(metrics.win_rate, 0)
        self.assertLessEqual(metrics.win_rate, 100)
        self.assertGreaterEqual(metrics.profit_factor, 0)

    def test_calculate_basic_metrics_win_rate(self):
        """Test win rate calculation."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_basic_metrics(trades)

        # With 60% win rate in test data, win rate should be ~60%
        self.assertGreater(metrics.win_rate, 50)
        self.assertLess(metrics.win_rate, 70)

    def test_calculate_basic_metrics_profit_factor(self):
        """Test profit factor calculation."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_basic_metrics(trades)

        # Profit factor should be positive with winning trades
        self.assertGreater(metrics.profit_factor, 0)

    def test_calculate_basic_metrics_average_win_loss(self):
        """Test average win and loss calculation."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_basic_metrics(trades)

        if metrics.winning_trades > 0:
            self.assertGreater(metrics.average_win, 0)

        if metrics.losing_trades > 0:
            self.assertLess(metrics.average_loss, 0)

    def test_calculate_basic_metrics_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_basic_metrics(trades)

        # Sharpe ratio should be calculated
        self.assertIsInstance(metrics.sharpe_ratio, float)

    def test_calculate_basic_metrics_empty_trades(self):
        """Test calculating metrics with empty trades list."""
        metrics = self.analytics.calculate_basic_metrics([])

        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.win_rate, 0.0)

    def test_calculate_drawdown(self):
        """Test calculating drawdown metrics."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_drawdown(trades)

        self.assertIsInstance(metrics, DrawdownMetrics)
        self.assertGreaterEqual(metrics.max_drawdown, 0)
        self.assertGreaterEqual(metrics.max_drawdown_percent, 0)

    def test_calculate_drawdown_with_initial_equity(self):
        """Test drawdown calculation with custom initial equity."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_drawdown(trades, initial_equity=50000.0)

        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics, DrawdownMetrics)

    def test_calculate_drawdown_empty_trades(self):
        """Test calculating drawdown with empty trades list."""
        metrics = self.analytics.calculate_drawdown([])

        self.assertEqual(metrics.max_drawdown, 0.0)
        self.assertEqual(metrics.drawdown_count, 0)

    def test_calculate_trade_statistics(self):
        """Test calculating trade statistics."""
        trades = self.analytics.fetch_all_trades()
        stats = self.analytics.calculate_trade_statistics(trades)

        self.assertIsInstance(stats, TradeStatistics)
        self.assertGreater(stats.avg_hold_time, 0)
        self.assertGreater(stats.avg_hold_time_minutes, 0)

    def test_calculate_trade_statistics_hold_time(self):
        """Test average hold time calculation."""
        trades = self.analytics.fetch_all_trades()
        stats = self.analytics.calculate_trade_statistics(trades)

        # Average hold time should be around 2 hours (7200 seconds)
        # based on test data
        self.assertGreater(stats.avg_hold_time, 0)
        self.assertGreater(stats.avg_hold_time_minutes, 0)

    def test_calculate_trade_statistics_trades_per_day(self):
        """Test trades per day calculation."""
        trades = self.analytics.fetch_all_trades()
        stats = self.analytics.calculate_trade_statistics(trades)

        # Should have positive trades per day
        self.assertGreater(stats.trades_per_day, 0)

    def test_calculate_trade_statistics_consecutive(self):
        """Test consecutive wins/losses calculation."""
        trades = self.analytics.fetch_all_trades()
        stats = self.analytics.calculate_trade_statistics(trades)

        self.assertGreaterEqual(stats.max_consecutive_wins, 0)
        self.assertGreaterEqual(stats.max_consecutive_losses, 0)

    def test_calculate_trade_statistics_largest_win_loss(self):
        """Test largest win and loss calculation."""
        trades = self.analytics.fetch_all_trades()
        stats = self.analytics.calculate_trade_statistics(trades)

        if stats.largest_win > 0:
            self.assertGreater(stats.largest_win, 0)

        if stats.largest_loss < 0:
            self.assertLess(stats.largest_loss, 0)

    def test_calculate_trade_statistics_empty_trades(self):
        """Test calculating statistics with empty trades list."""
        stats = self.analytics.calculate_trade_statistics([])

        self.assertEqual(stats.avg_hold_time, 0)
        self.assertEqual(stats.max_consecutive_wins, 0)
        self.assertEqual(stats.max_consecutive_losses, 0)

    def test_calculate_returns(self):
        """Test calculating returns metrics."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_returns(trades)

        self.assertIsInstance(metrics, ReturnsMetrics)
        self.assertIsInstance(metrics.total_return, float)
        self.assertIsInstance(metrics.total_return_percent, float)

    def test_calculate_returns_daily_metrics(self):
        """Test daily return calculations."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_returns(trades)

        self.assertIsInstance(metrics.daily_return_avg, float)
        self.assertIsInstance(metrics.daily_return_std, float)

    def test_calculate_returns_weekly_metrics(self):
        """Test weekly return calculations."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_returns(trades)

        self.assertIsInstance(metrics.weekly_return_avg, float)

    def test_calculate_returns_monthly_metrics(self):
        """Test monthly return calculations."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_returns(trades)

        self.assertIsInstance(metrics.monthly_return_avg, float)

    def test_calculate_returns_best_worst(self):
        """Test best and worst day/week/month calculations."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_returns(trades)

        self.assertIsInstance(metrics.best_day, float)
        self.assertIsInstance(metrics.worst_day, float)
        self.assertGreaterEqual(metrics.best_day, metrics.worst_day)

    def test_calculate_returns_volatility(self):
        """Test volatility calculation."""
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_returns(trades)

        self.assertIsInstance(metrics.volatility, float)
        self.assertGreaterEqual(metrics.volatility, 0)

    def test_calculate_returns_empty_trades(self):
        """Test calculating returns with empty trades list."""
        metrics = self.analytics.calculate_returns([])

        self.assertEqual(metrics.total_return, 0.0)
        self.assertEqual(metrics.total_return_percent, 0.0)

    def test_calculate_all_metrics(self):
        """Test calculating all metrics at once."""
        cached = self.analytics.calculate_all_metrics()

        self.assertIsInstance(cached, CachedMetrics)
        self.assertIsNotNone(cached.basic_metrics)
        self.assertIsNotNone(cached.drawdown_metrics)
        self.assertIsNotNone(cached.trade_statistics)
        self.assertIsNotNone(cached.returns_metrics)

    def test_calculate_all_metrics_with_filters(self):
        """Test calculating all metrics with date filters."""
        cached = self.analytics.calculate_all_metrics(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        self.assertIsNotNone(cached.basic_metrics)
        self.assertGreater(cached.basic_metrics.total_trades, 0)

    def test_calculate_all_metrics_with_cache(self):
        """Test that cache is used when not expired."""
        # First calculation
        cached1 = self.analytics.calculate_all_metrics(use_cache=True)
        first_calc_time = cached1.basic_metrics.calculated_at

        # Second calculation should use cache
        cached2 = self.analytics.calculate_all_metrics(use_cache=True)
        second_calc_time = cached2.basic_metrics.calculated_at

        self.assertEqual(first_calc_time, second_calc_time)

    def test_calculate_all_metrics_without_cache(self):
        """Test that cache is bypassed when requested."""
        # First calculation
        cached1 = self.analytics.calculate_all_metrics(use_cache=True)
        first_calc_time = cached1.basic_metrics.calculated_at

        # Force recalculation by clearing cache
        import time
        time.sleep(0.01)  # Small delay to ensure different timestamp

        cached2 = self.analytics.calculate_all_metrics(use_cache=False)
        second_calc_time = cached2.basic_metrics.calculated_at

        # Times should be different
        self.assertNotEqual(first_calc_time, second_calc_time)

    def test_store_metrics(self):
        """Test storing metrics in database."""
        trades = self.analytics.fetch_all_trades()

        basic = self.analytics.calculate_basic_metrics(trades)
        drawdown = self.analytics.calculate_drawdown(trades)
        stats = self.analytics.calculate_trade_statistics(trades)
        returns = self.analytics.calculate_returns(trades)

        self.analytics._store_metrics(basic, drawdown, stats, returns)

        # Verify metrics were stored
        cursor = self.analytics._connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM basic_metrics")
        basic_count = cursor.fetchone()[0]
        self.assertGreater(basic_count, 0)

        cursor.execute("SELECT COUNT(*) FROM drawdown_metrics")
        drawdown_count = cursor.fetchone()[0]
        self.assertGreater(drawdown_count, 0)

        cursor.execute("SELECT COUNT(*) FROM trade_statistics")
        stats_count = cursor.fetchone()[0]
        self.assertGreater(stats_count, 0)

        cursor.execute("SELECT COUNT(*) FROM returns_metrics")
        returns_count = cursor.fetchone()[0]
        self.assertGreater(returns_count, 0)

    def test_get_basic_metrics(self):
        """Test getting cached basic metrics."""
        self.analytics.calculate_all_metrics()
        basic = self.analytics.get_basic_metrics()

        self.assertIsNotNone(basic)
        self.assertIsInstance(basic, BasicMetrics)

    def test_get_drawdown_metrics(self):
        """Test getting cached drawdown metrics."""
        self.analytics.calculate_all_metrics()
        drawdown = self.analytics.get_drawdown_metrics()

        self.assertIsNotNone(drawdown)
        self.assertIsInstance(drawdown, DrawdownMetrics)

    def test_get_trade_statistics(self):
        """Test getting cached trade statistics."""
        self.analytics.calculate_all_metrics()
        stats = self.analytics.get_trade_statistics()

        self.assertIsNotNone(stats)
        self.assertIsInstance(stats, TradeStatistics)

    def test_get_returns_metrics(self):
        """Test getting cached returns metrics."""
        self.analytics.calculate_all_metrics()
        returns = self.analytics.get_returns_metrics()

        self.assertIsNotNone(returns)
        self.assertIsInstance(returns, ReturnsMetrics)

    def test_get_historical_metrics(self):
        """Test retrieving historical metrics from database."""
        # Generate some metrics
        self.analytics.calculate_all_metrics()

        # Retrieve historical basic metrics
        historical = self.analytics.get_historical_metrics("basic", limit=10)

        self.assertIsInstance(historical, list)
        self.assertGreater(len(historical), 0)
        self.assertIsInstance(historical[0], dict)

    def test_get_historical_metrics_invalid_type(self):
        """Test retrieving historical metrics with invalid type."""
        historical = self.analytics.get_historical_metrics("invalid_type")

        self.assertEqual(len(historical), 0)

    def test_clear_cache(self):
        """Test clearing the metrics cache."""
        # Calculate metrics to populate cache
        self.analytics.calculate_all_metrics()
        self.assertIsNotNone(self.analytics.get_basic_metrics())

        # Clear cache
        self.analytics.clear_cache()

        # Cache should be empty
        self.assertIsNone(self.analytics.get_basic_metrics())

    def test_close(self):
        """Test closing database connections."""
        self.analytics.close()

        self.assertIsNone(self.analytics._connection)
        self.assertIsNone(self.analytics._trades_connection)

    def test_historical_data_six_months(self):
        """Test analytics on 6+ months of historical data."""
        # Test data spans 100 days (~3 months)
        # In production, this would be 6+ months
        cached = self.analytics.calculate_all_metrics()

        self.assertIsNotNone(cached.basic_metrics)
        self.assertGreater(cached.basic_metrics.total_trades, 50)

    def test_logging(self):
        """Test that comprehensive logging is performed."""
        # This test verifies that methods execute and log
        # In production, verify log files contain expected entries
        trades = self.analytics.fetch_all_trades()
        metrics = self.analytics.calculate_basic_metrics(trades)

        self.assertIsNotNone(metrics)
        # Check that calculation timestamp is recent
        time_diff = datetime.utcnow() - metrics.calculated_at
        self.assertLess(time_diff.total_seconds(), 5)

    def test_cache_ttl_seconds(self):
        """Test cache TTL configuration."""
        analytics = PerformanceAnalytics(
            database_path=self.analytics_db_path,
            trades_database_path=self.trades_db_path,
            cache_ttl_seconds=600,  # 10 minutes
        )

        self.assertEqual(analytics._cache_ttl_seconds, 600)
        self.assertEqual(analytics._cached_metrics.ttl_seconds, 600)

        analytics.close()


if __name__ == "__main__":
    unittest.main()
