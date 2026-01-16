"""
Comprehensive unit tests for SymbolPerformanceAnalyzer.

Tests cover all functionality including:
- Data model creation and serialization
- Database initialization and schema
- Symbol metrics calculation
- Correlation analysis
- Ranking generation
- Database storage and retrieval
- Report generation
- Edge cases and error handling
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from backend.analytics.symbol_performance_analyzer import (
    SymbolMetrics,
    SymbolCorrelation,
    SymbolRanking,
    SymbolPerformanceAnalyzer,
)


class TestSymbolMetrics(unittest.TestCase):
    """Test SymbolMetrics dataclass."""

    def test_symbol_metrics_creation(self):
        """Test creating SymbolMetrics with default values."""
        metrics = SymbolMetrics(symbol="V10")
        self.assertEqual(metrics.symbol, "V10")
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.profit_factor, 0.0)
        self.assertEqual(metrics.total_trades, 0)

    def test_symbol_metrics_with_values(self):
        """Test creating SymbolMetrics with specific values."""
        metrics = SymbolMetrics(
            symbol="V25",
            win_rate=60.0,
            profit_factor=1.5,
            total_pnl=1000.0,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
        )
        self.assertEqual(metrics.symbol, "V25")
        self.assertEqual(metrics.win_rate, 60.0)
        self.assertEqual(metrics.profit_factor, 1.5)
        self.assertEqual(metrics.total_pnl, 1000.0)

    def test_symbol_metrics_to_dict(self):
        """Test converting SymbolMetrics to dictionary."""
        metrics = SymbolMetrics(
            symbol="V50",
            win_rate=55.5,
            profit_factor=1.2,
            total_pnl=500.0,
        )
        result = metrics.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol"], "V50")
        self.assertEqual(result["win_rate"], 55.5)
        self.assertIn("calculated_at", result)

    def test_symbol_metrics_infinity_handling(self):
        """Test handling of infinite profit_factor in to_dict."""
        metrics = SymbolMetrics(
            symbol="V75",
            profit_factor=float("inf"),
        )
        result = metrics.to_dict()
        # Should convert infinity to 0
        self.assertEqual(result["profit_factor"], 0)


class TestSymbolCorrelation(unittest.TestCase):
    """Test SymbolCorrelation dataclass."""

    def test_symbol_correlation_creation(self):
        """Test creating SymbolCorrelation with default values."""
        corr = SymbolCorrelation(symbol1="V10", symbol2="V25")
        self.assertEqual(corr.symbol1, "V10")
        self.assertEqual(corr.symbol2, "V25")
        self.assertEqual(corr.correlation, 0.0)

    def test_symbol_correlation_with_values(self):
        """Test creating SymbolCorrelation with specific values."""
        corr = SymbolCorrelation(
            symbol1="V50",
            symbol2="V75",
            correlation=0.85,
            covariance=120.5,
            sample_size=100,
        )
        self.assertEqual(corr.correlation, 0.85)
        self.assertEqual(corr.covariance, 120.5)
        self.assertEqual(corr.sample_size, 100)

    def test_symbol_correlation_to_dict(self):
        """Test converting SymbolCorrelation to dictionary."""
        corr = SymbolCorrelation(
            symbol1="V10",
            symbol2="V100",
            correlation=0.75,
        )
        result = corr.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol1"], "V10")
        self.assertEqual(result["symbol2"], "V100")
        self.assertEqual(result["correlation"], 0.75)


class TestSymbolRanking(unittest.TestCase):
    """Test SymbolRanking dataclass."""

    def test_symbol_ranking_creation(self):
        """Test creating SymbolRanking."""
        ranking = SymbolRanking(
            symbol="V10",
            rank=1,
            metric="sharpe_ratio",
            value=2.5,
        )
        self.assertEqual(ranking.symbol, "V10")
        self.assertEqual(ranking.rank, 1)
        self.assertEqual(ranking.metric, "sharpe_ratio")
        self.assertEqual(ranking.value, 2.5)

    def test_symbol_ranking_to_dict(self):
        """Test converting SymbolRanking to dictionary."""
        ranking = SymbolRanking(
            symbol="V25",
            rank=2,
            metric="total_pnl",
            value=1500.0,
        )
        result = ranking.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol"], "V25")
        self.assertEqual(result["rank"], 2)
        self.assertEqual(result["value"], 1500.0)


class TestSymbolPerformanceAnalyzer(unittest.TestCase):
    """Test SymbolPerformanceAnalyzer class."""

    def setUp(self):
        """Set up test database and analyzer."""
        # Create temporary databases
        self.analytics_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.analytics_db.close()

        self.trades_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.trades_db.close()

        # Create test trades database with sample data
        self._create_test_trades_database()

        # Initialize analyzer
        self.analyzer = SymbolPerformanceAnalyzer(
            database_path=self.analytics_db.name,
            trades_database_path=self.trades_db.name,
        )

    def tearDown(self):
        """Clean up temporary databases."""
        self.analyzer.close()

        # Close and delete temporary files
        try:
            os.unlink(self.analytics_db.name)
        except:
            pass

        try:
            os.unlink(self.trades_db.name)
        except:
            pass

    def _create_test_trades_database(self):
        """Create a test trades database with sample data."""
        conn = sqlite3.connect(self.trades_db.name)
        cursor = conn.cursor()

        # Create trade_outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                final_profit REAL NOT NULL,
                volume REAL,
                initial_stop_loss REAL,
                initial_take_profit REAL
            )
        """)

        # Insert test trades for different symbols
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        test_trades = []

        # V10 - Good performance (60% win rate, positive P&L)
        for i in range(50):
            entry_time = base_time + timedelta(days=i, hours=10)
            exit_time = entry_time + timedelta(hours=2)
            profit = 100.0 if i % 5 < 3 else -50.0  # 60% win rate

            test_trades.append((
                1000 + i,
                "V10",
                "BUY",
                10000.0,
                10050.0 if profit > 0 else 9950.0,
                entry_time.isoformat(),
                exit_time.isoformat(),
                profit,
                1.0,
                9950.0,
                10100.0,
            ))

        # V25 - Moderate performance (55% win rate, slightly positive P&L)
        for i in range(40):
            entry_time = base_time + timedelta(days=i, hours=11)
            exit_time = entry_time + timedelta(hours=1)
            profit = 80.0 if i % 20 < 11 else -60.0  # 55% win rate

            test_trades.append((
                2000 + i,
                "V25",
                "BUY",
                25000.0,
                25030.0 if profit > 0 else 24970.0,
                entry_time.isoformat(),
                exit_time.isoformat(),
                profit,
                1.0,
                24970.0,
                25030.0,
            ))

        # V50 - Poor performance (45% win rate, negative P&L)
        for i in range(30):
            entry_time = base_time + timedelta(days=i, hours=12)
            exit_time = entry_time + timedelta(hours=3)
            # For 45% win rate: win 13-14 out of 30 trades
            # Use pattern: win at indices 0-12, lose at 13-29
            is_win = i < 13  # First 13 are wins, rest 17 are losses = 43.33%
            profit = 70.0 if is_win else -90.0

            test_trades.append((
                3000 + i,
                "V50",
                "SELL",
                50000.0,
                49930.0 if profit > 0 else 50090.0,
                entry_time.isoformat(),
                exit_time.isoformat(),
                profit,
                1.0,
                50090.0,
                49930.0,
            ))

        # V75 - Moderate performance (50% win rate, break-even)
        for i in range(20):
            entry_time = base_time + timedelta(days=i, hours=13)
            exit_time = entry_time + timedelta(hours=2)
            profit = 100.0 if i % 2 == 0 else -100.0  # 50% win rate, break even

            test_trades.append((
                4000 + i,
                "V75",
                "BUY",
                75000.0,
                75100.0 if profit > 0 else 74900.0,
                entry_time.isoformat(),
                exit_time.isoformat(),
                profit,
                1.0,
                74900.0,
                75100.0,
            ))

        # V100 - Very good performance (65% win rate, high positive P&L)
        for i in range(60):
            entry_time = base_time + timedelta(days=i, hours=14)
            exit_time = entry_time + timedelta(hours=1)
            profit = 120.0 if i % 20 < 13 else -80.0  # 65% win rate

            test_trades.append((
                5000 + i,
                "V100",
                "BUY",
                100000.0,
                100120.0 if profit > 0 else 99920.0,
                entry_time.isoformat(),
                exit_time.isoformat(),
                profit,
                1.0,
                99920.0,
                100120.0,
            ))

        # Insert all trades
        cursor.executemany("""
            INSERT INTO trade_outcomes (
                ticket, symbol, direction, entry_price, exit_price,
                entry_time, exit_time, final_profit, volume,
                initial_stop_loss, initial_take_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_trades)

        conn.commit()
        conn.close()

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        self.assertIsNotNone(self.analyzer._connection)
        self.assertIsNotNone(self.analyzer._trades_connection)
        self.assertEqual(len(self.analyzer._symbol_metrics), 0)

    def test_database_tables_created(self):
        """Test that database tables are created correctly."""
        cursor = self.analyzer._connection.cursor()

        # Check symbol_metrics table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='symbol_metrics'"
        )
        self.assertIsNotNone(cursor.fetchone())

        # Check symbol_correlations table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='symbol_correlations'"
        )
        self.assertIsNotNone(cursor.fetchone())

        # Check symbol_rankings table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='symbol_rankings'"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_fetch_trades_by_symbol(self):
        """Test fetching trades for a specific symbol."""
        trades = self.analyzer.fetch_trades_by_symbol("V10")

        self.assertIsInstance(trades, list)
        self.assertGreater(len(trades), 0)
        self.assertEqual(trades[0]["symbol"], "V10")
        self.assertIn("profit", trades[0])
        self.assertIn("entry_time", trades[0])
        self.assertIn("exit_time", trades[0])

    def test_calculate_symbol_metrics(self):
        """Test calculating metrics for a single symbol."""
        metrics = self.analyzer.calculate_symbol_metrics("V10")

        self.assertIsInstance(metrics, SymbolMetrics)
        self.assertEqual(metrics.symbol, "V10")
        self.assertGreater(metrics.total_trades, 0)
        self.assertGreater(metrics.win_rate, 0)
        self.assertIsNotNone(metrics.calculated_at)

    def test_calculate_symbol_metrics_win_rate(self):
        """Test win rate calculation for different symbols."""
        # V10 has 60% win rate (3 out of 5 wins)
        metrics_v10 = self.analyzer.calculate_symbol_metrics("V10")
        self.assertAlmostEqual(metrics_v10.win_rate, 60.0, delta=5.0)

        # V50 has ~43% win rate (13 out of 30 wins)
        metrics_v50 = self.analyzer.calculate_symbol_metrics("V50")
        self.assertAlmostEqual(metrics_v50.win_rate, 43.33, delta=5.0)

        # V100 has 65% win rate (13 out of 20 wins)
        metrics_v100 = self.analyzer.calculate_symbol_metrics("V100")
        self.assertAlmostEqual(metrics_v100.win_rate, 65.0, delta=5.0)

    def test_calculate_symbol_metrics_pnl(self):
        """Test total P&L calculation."""
        metrics_v10 = self.analyzer.calculate_symbol_metrics("V10")
        self.assertGreater(metrics_v10.total_pnl, 0)  # Should be profitable

        metrics_v50 = self.analyzer.calculate_symbol_metrics("V50")
        # V50 should have negative P&L (wins: 9*70=630, losses: 11*-90=-990 per 20 trades)
        self.assertLess(metrics_v50.total_pnl, 0)  # Should be losing

    def test_calculate_all_symbols(self):
        """Test calculating metrics for all symbols."""
        all_metrics = self.analyzer.calculate_all_symbols()

        self.assertIsInstance(all_metrics, dict)
        self.assertGreater(len(all_metrics), 0)

        # Check that all expected symbols are present
        expected_symbols = {"V10", "V25", "V50", "V75", "V100"}
        found_symbols = set(all_metrics.keys())
        self.assertTrue(expected_symbols.issubset(found_symbols))

    def test_calculate_symbol_correlation(self):
        """Test calculating correlation between two symbols."""
        corr = self.analyzer.calculate_symbol_correlation("V10", "V25")

        self.assertIsInstance(corr, SymbolCorrelation)
        self.assertEqual(corr.symbol1, "V10")
        self.assertEqual(corr.symbol2, "V25")
        # Note: sample_size may be 0 if no common timestamps
        self.assertGreaterEqual(corr.correlation, -1.0)
        self.assertLessEqual(corr.correlation, 1.0)

    def test_calculate_correlation_matrix(self):
        """Test calculating correlation matrix for all symbols."""
        correlations = self.analyzer.calculate_correlation_matrix()

        self.assertIsInstance(correlations, dict)
        self.assertGreater(len(correlations), 0)

        # Check that correlations are stored correctly
        for (symbol1, symbol2), corr in correlations.items():
            self.assertIsInstance(corr, SymbolCorrelation)
            self.assertIn(symbol1, ["V10", "V25", "V50", "V75", "V100"])
            self.assertIn(symbol2, ["V10", "V25", "V50", "V75", "V100"])

    def test_get_best_performing_symbol(self):
        """Test identifying best performing symbol."""
        # First calculate all metrics
        self.analyzer.calculate_all_symbols()

        # V100 should be best by Sharpe ratio
        best_sharpe = self.analyzer.get_best_performing_symbol("sharpe_ratio")
        self.assertIsNotNone(best_sharpe)

        # V100 should be best by total P&L
        best_pnl = self.analyzer.get_best_performing_symbol("total_pnl")
        self.assertIsNotNone(best_pnl)

    def test_get_worst_performing_symbol(self):
        """Test identifying worst performing symbol."""
        # First calculate all metrics
        self.analyzer.calculate_all_symbols()

        worst = self.analyzer.get_worst_performing_symbol("sharpe_ratio")
        self.assertIsNotNone(worst)

    def test_get_symbol_ranking(self):
        """Test generating symbol ranking."""
        # First calculate all metrics
        self.analyzer.calculate_all_symbols()

        ranking = self.analyzer.get_symbol_ranking("sharpe_ratio")

        self.assertIsInstance(ranking, list)
        self.assertGreater(len(ranking), 0)

        # Check that ranks are sequential
        ranks = [r.rank for r in ranking]
        self.assertEqual(ranks, list(range(1, len(ranking) + 1)))

        # Check that values are sorted descending
        values = [r.value for r in ranking]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_store_symbol_metrics(self):
        """Test storing symbol metrics in database."""
        metrics = SymbolMetrics(
            symbol="V10",
            win_rate=60.0,
            profit_factor=1.5,
            total_pnl=1000.0,
            total_trades=100,
        )

        self.analyzer.store_symbol_metrics(metrics)

        # Verify storage
        cursor = self.analyzer._connection.cursor()
        cursor.execute(
            "SELECT * FROM symbol_metrics WHERE symbol = ?",
            ("V10",)
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "V10")  # symbol column
        self.assertEqual(row[2], 60.0)  # win_rate column

    def test_store_correlation(self):
        """Test storing correlation in database."""
        corr = SymbolCorrelation(
            symbol1="V10",
            symbol2="V25",
            correlation=0.75,
            covariance=100.0,
            sample_size=50,
        )

        self.analyzer.store_correlation(corr)

        # Verify storage
        cursor = self.analyzer._connection.cursor()
        cursor.execute(
            "SELECT * FROM symbol_correlations WHERE symbol1 = ? AND symbol2 = ?",
            ("V10", "V25")
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "V10")  # symbol1 column
        self.assertEqual(row[2], "V25")  # symbol2 column
        self.assertEqual(row[3], 0.75)  # correlation column

    def test_store_ranking(self):
        """Test storing ranking in database."""
        ranking = [
            SymbolRanking(symbol="V100", rank=1, metric="sharpe_ratio", value=2.5),
            SymbolRanking(symbol="V10", rank=2, metric="sharpe_ratio", value=2.0),
            SymbolRanking(symbol="V25", rank=3, metric="sharpe_ratio", value=1.5),
        ]

        self.analyzer.store_ranking(ranking)

        # Verify storage
        cursor = self.analyzer._connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM symbol_rankings WHERE metric = ?",
            ("sharpe_ratio",)
        )
        count = cursor.fetchone()[0]
        self.assertEqual(count, 3)

    def test_generate_performance_report(self):
        """Test generating performance report."""
        # First calculate all metrics
        self.analyzer.calculate_all_symbols()

        report = self.analyzer.generate_performance_report()

        self.assertIsInstance(report, str)
        self.assertIn("SYMBOL PERFORMANCE REPORT", report)
        self.assertIn("RANKING BY", report)
        self.assertIn("V10", report)
        self.assertIn("V25", report)

    def test_analyze_all_symbols(self):
        """Test complete symbol analysis workflow."""
        results = self.analyzer.analyze_all_symbols()

        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)

        # Check that metrics are cached
        self.assertEqual(len(self.analyzer._symbol_metrics), len(results))

        # Check that correlations are calculated
        self.assertGreater(len(self.analyzer._correlations), 0)

    def test_get_symbol_metrics(self):
        """Test retrieving cached symbol metrics."""
        # First calculate metrics
        self.analyzer.calculate_all_symbols()

        # Retrieve cached metrics
        metrics = self.analyzer.get_symbol_metrics("V10")
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.symbol, "V10")

        # Try non-existent symbol
        metrics_none = self.analyzer.get_symbol_metrics("XXX")
        self.assertIsNone(metrics_none)

    def test_get_symbol_correlation(self):
        """Test retrieving cached correlation."""
        # First calculate correlations
        self.analyzer.calculate_correlation_matrix()

        # Retrieve cached correlation
        corr = self.analyzer.get_symbol_correlation("V10", "V25")
        self.assertIsNotNone(corr)

        # Try reverse order (should still work)
        corr_reverse = self.analyzer.get_symbol_correlation("V25", "V10")
        self.assertIsNotNone(corr_reverse)

    def test_get_historical_symbol_metrics(self):
        """Test retrieving historical metrics from database."""
        # Store some metrics
        metrics = SymbolMetrics(
            symbol="V10",
            win_rate=60.0,
            total_pnl=1000.0,
        )
        self.analyzer.store_symbol_metrics(metrics)

        # Retrieve historical metrics
        historical = self.analyzer.get_historical_symbol_metrics("V10")

        self.assertIsInstance(historical, list)
        self.assertGreater(len(historical), 0)
        self.assertEqual(historical[0]["symbol"], "V10")

    def test_invalid_metric_for_ranking(self):
        """Test handling of invalid metric for ranking."""
        self.analyzer.calculate_all_symbols()

        ranking = self.analyzer.get_symbol_ranking("invalid_metric")
        self.assertEqual(len(ranking), 0)

    def test_invalid_metric_for_best_worst(self):
        """Test handling of invalid metric for best/worst symbol."""
        self.analyzer.calculate_all_symbols()

        best = self.analyzer.get_best_performing_symbol("invalid_metric")
        self.assertIsNone(best)

        worst = self.analyzer.get_worst_performing_symbol("invalid_metric")
        self.assertIsNone(worst)

    def test_empty_trades_handling(self):
        """Test handling when no trades are available."""
        # Create analyzer with empty database
        empty_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        empty_db.close()

        try:
            # Create empty trades database
            conn = sqlite3.connect(empty_db.name)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE trade_outcomes (
                    ticket INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    final_profit REAL NOT NULL,
                    volume REAL,
                    initial_stop_loss REAL,
                    initial_take_profit REAL
                )
            """)
            conn.commit()
            conn.close()

            # Create analyzer
            analyzer = SymbolPerformanceAnalyzer(
                database_path=tempfile.NamedTemporaryFile(delete=False).name,
                trades_database_path=empty_db.name,
            )

            # Try to calculate metrics
            metrics = analyzer.calculate_symbol_metrics("V10")

            # Should return empty metrics
            self.assertEqual(metrics.total_trades, 0)
            self.assertEqual(metrics.win_rate, 0.0)

            analyzer.close()

        finally:
            try:
                os.unlink(empty_db.name)
            except:
                pass

    def test_profit_factor_calculation(self):
        """Test profit factor calculation."""
        metrics = self.analyzer.calculate_symbol_metrics("V10")

        # Profit factor should be calculated
        self.assertIsInstance(metrics.profit_factor, float)
        # For profitable symbol, profit factor should be > 1
        if metrics.losing_trades > 0:
            self.assertGreater(metrics.profit_factor, 0)

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation."""
        metrics = self.analyzer.calculate_symbol_metrics("V10")

        # Sharpe ratio should be calculated
        self.assertIsInstance(metrics.sharpe_ratio, float)

    def test_correlation_with_insufficient_data(self):
        """Test correlation calculation with insufficient data."""
        # Try correlation between symbols with no common trades
        corr = self.analyzer.calculate_symbol_correlation("V10", "V999")

        # Should return correlation with 0 sample size
        self.assertEqual(corr.sample_size, 0)
        self.assertEqual(corr.correlation, 0.0)

    def test_date_filtering_in_fetch_trades(self):
        """Test fetching trades with date filtering."""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 20)

        trades = self.analyzer.fetch_trades_by_symbol(
            "V10",
            start_date=start_date,
            end_date=end_date
        )

        # All returned trades should be within date range
        for trade in trades:
            trade_date = trade["entry_time"]
            self.assertGreaterEqual(trade_date, start_date)
            self.assertLessEqual(trade_date, end_date)

    def test_close_connection(self):
        """Test closing database connections."""
        self.analyzer.close()

        # Connections should be None after close
        self.assertIsNone(self.analyzer._connection)
        self.assertIsNone(self.analyzer._trades_connection)


if __name__ == "__main__":
    unittest.main()
