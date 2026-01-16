"""
Symbol Performance Analyzer for analyzing trading performance by volatility indices.

This module implements comprehensive symbol-based performance analysis to identify
which volatility indices (V10, V25, V50, V75, V100) are most profitable.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SymbolMetrics:
    """
    Performance metrics for a single trading symbol.

    Attributes:
        symbol: Trading symbol (e.g., "V10", "V25", "V50", "V75", "V100")
        win_rate: Percentage of winning trades (0-100)
        profit_factor: Ratio of total profit to total loss
        total_pnl: Total profit/loss for this symbol
        total_trades: Number of trades for this symbol
        winning_trades: Number of profitable trades
        losing_trades: Number of unprofitable trades
        average_win: Average profit per winning trade
        average_loss: Average loss per losing trade
        largest_win: Largest single winning trade
        largest_loss: Largest single losing trade
        sharpe_ratio: Risk-adjusted return metric
        avg_hold_time: Average hold time in seconds
        calculated_at: When metrics were calculated
    """

    symbol: str
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    sharpe_ratio: float = 0.0
    avg_hold_time: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage/serialization."""
        return {
            "symbol": self.symbol,
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2) if self.profit_factor != float("inf") else 0,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "average_win": round(self.average_win, 2),
            "average_loss": round(self.average_loss, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "avg_hold_time": round(self.avg_hold_time, 2),
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class SymbolCorrelation:
    """
    Correlation data between two symbols.

    Attributes:
        symbol1: First symbol (e.g., "V10")
        symbol2: Second symbol (e.g., "V25")
        correlation: Correlation coefficient (-1 to 1)
        covariance: Covariance between symbols
        sample_size: Number of data points used
        calculated_at: When correlation was calculated
    """

    symbol1: str
    symbol2: str
    correlation: float = 0.0
    covariance: float = 0.0
    sample_size: int = 0
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert correlation to dictionary for storage."""
        return {
            "symbol1": self.symbol1,
            "symbol2": self.symbol2,
            "correlation": round(self.correlation, 4),
            "covariance": round(self.covariance, 4),
            "sample_size": self.sample_size,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class SymbolRanking:
    """
    Ranking of symbols by performance metric.

    Attributes:
        symbol: Trading symbol
        rank: Position in ranking (1 = best)
        metric: Metric used for ranking (e.g., "sharpe_ratio", "total_pnl")
        value: Value of the metric for this symbol
        calculated_at: When ranking was calculated
    """

    symbol: str
    rank: int
    metric: str
    value: float
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert ranking to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "rank": self.rank,
            "metric": self.metric,
            "value": round(self.value, 4),
            "calculated_at": self.calculated_at.isoformat(),
        }


class SymbolPerformanceAnalyzer:
    """
    Comprehensive symbol-based performance analyzer.

    Features:
    - Calculate win rate for each symbol
    - Calculate profit factor for each symbol
    - Calculate total P&L for each symbol
    - Calculate Sharpe ratio for each symbol
    - Identify best and worst performing symbols
    - Calculate symbol correlation matrix
    - Generate symbol performance ranking
    - Store symbol metrics in database
    - Generate symbol performance report

    Usage:
        analyzer = SymbolPerformanceAnalyzer(database_path="performance_analytics.db")

        # Calculate all symbol metrics
        analyzer.analyze_all_symbols()

        # Get metrics for a specific symbol
        metrics = analyzer.get_symbol_metrics("V10")
        print(f"V10 Win Rate: {metrics.win_rate}%")

        # Get symbol ranking
        ranking = analyzer.get_symbol_ranking(metric="sharpe_ratio")
        print(f"Best symbol: {ranking[0].symbol}")

        # Get symbol correlation
        correlation = analyzer.get_symbol_correlation("V10", "V25")
        print(f"V10-V25 Correlation: {correlation.correlation}")

        # Generate performance report
        report = analyzer.generate_performance_report()
        print(report)
    """

    def __init__(
        self,
        database_path: str = "performance_analytics.db",
        trades_database_path: str = "trades.db",
    ):
        """
        Initialize the SymbolPerformanceAnalyzer.

        Args:
            database_path: Path to SQLite database for storing analytics data
            trades_database_path: Path to database containing trade records
        """
        self._database_path = database_path
        self._trades_database_path = trades_database_path
        self._connection: Optional[sqlite3.Connection] = None
        self._trades_connection: Optional[sqlite3.Connection] = None
        self._symbol_metrics: dict[str, SymbolMetrics] = {}
        self._correlations: dict[tuple[str, str], SymbolCorrelation] = {}

        # Initialize databases
        self._initialize_database()
        self._initialize_trades_connection()

        logger.info(
            f"SymbolPerformanceAnalyzer initialized with database: {database_path}, "
            f"trades database: {trades_database_path}"
        )

    def _initialize_database(self) -> None:
        """
        Initialize the analytics database with required tables.

        Creates tables for:
        - symbol_metrics: Historical symbol performance metrics
        - symbol_correlations: Correlation data between symbol pairs
        - symbol_rankings: Historical symbol rankings
        """
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create symbol_metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbol_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    win_rate REAL NOT NULL,
                    profit_factor REAL NOT NULL,
                    total_pnl REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    winning_trades INTEGER NOT NULL,
                    losing_trades INTEGER NOT NULL,
                    average_win REAL NOT NULL,
                    average_loss REAL NOT NULL,
                    largest_win REAL NOT NULL,
                    largest_loss REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    avg_hold_time REAL NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, calculated_at)
                )
            """)

            # Create symbol_correlations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbol_correlations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol1 TEXT NOT NULL,
                    symbol2 TEXT NOT NULL,
                    correlation REAL NOT NULL,
                    covariance REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol1, symbol2, calculated_at)
                )
            """)

            # Create symbol_rankings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbol_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, metric, calculated_at)
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_metrics_symbol
                ON symbol_metrics(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_metrics_calculated_at
                ON symbol_metrics(calculated_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_correlations_symbol1
                ON symbol_correlations(symbol1)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_correlations_symbol2
                ON symbol_correlations(symbol2)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_rankings_metric
                ON symbol_rankings(metric)
            """)

            self._connection.commit()

            logger.info("Symbol performance database tables initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize symbol performance database: {e}")
            raise

    def _initialize_trades_connection(self) -> None:
        """Initialize connection to the trades database."""
        try:
            self._trades_connection = sqlite3.connect(self._trades_database_path)
            logger.info(f"Connected to trades database: {self._trades_database_path}")
        except sqlite3.Error as e:
            logger.warning(f"Failed to connect to trades database: {e}")
            self._trades_connection = None

    def fetch_trades_by_symbol(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all trades for a specific symbol from the database.

        Args:
            symbol: Trading symbol to filter by
            start_date: Filter trades from this date onwards (optional)
            end_date: Filter trades up to this date (optional)

        Returns:
            List of trade dictionaries
        """
        if self._trades_connection is None:
            logger.warning("No trades database connection available")
            return []

        try:
            cursor = self._trades_connection.cursor()

            query = """
                SELECT ticket, symbol, direction, entry_price, exit_price,
                       entry_time, exit_time, final_profit, volume,
                       initial_stop_loss, initial_take_profit
                FROM trade_outcomes
                WHERE symbol = ?
            """

            params: list[Any] = [symbol]

            if start_date is not None:
                query += " AND entry_time >= ?"
                params.append(start_date.isoformat())

            if end_date is not None:
                query += " AND entry_time <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY entry_time ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to dictionaries
            trades = []
            for row in rows:
                try:
                    trade = {
                        "ticket": row[0],
                        "symbol": row[1],
                        "direction": row[2],
                        "entry_price": row[3],
                        "exit_price": row[4] if row[4] else 0.0,
                        "entry_time": datetime.fromisoformat(row[5]),
                        "exit_time": datetime.fromisoformat(row[6]) if row[6] else None,
                        "profit": row[7],
                        "volume": row[8] if row[8] else 1.0,
                        "stop_loss": row[9] if len(row) > 9 and row[9] else None,
                        "take_profit": row[10] if len(row) > 10 and row[10] else None,
                    }
                    trades.append(trade)
                except Exception as e:
                    logger.debug(f"Failed to parse trade row: {e}")
                    continue

            logger.info(
                f"Fetched {len(trades)} trades for symbol {symbol} "
                f"(start_date={start_date}, end_date={end_date})"
            )

            return trades

        except sqlite3.Error as e:
            logger.error(f"Failed to fetch trades for symbol {symbol}: {e}")
            return []

    def calculate_symbol_metrics(
        self,
        symbol: str,
        trades: Optional[list[dict[str, Any]]] = None,
    ) -> SymbolMetrics:
        """
        Calculate performance metrics for a specific symbol.

        Metrics calculated:
        - Win rate: Percentage of winning trades
        - Profit factor: Ratio of total profit to total loss
        - Total P&L: Sum of all profits and losses
        - Sharpe ratio: Risk-adjusted return (assuming 5% risk-free rate)
        - Average win/loss: Average profit per winning/losing trade
        - Largest win/loss: Best and worst single trades
        - Average hold time: Average time positions were held

        Args:
            symbol: Trading symbol to analyze
            trades: List of trades to analyze. If None, fetches from database.

        Returns:
            SymbolMetrics object with calculated metrics
        """
        if trades is None:
            trades = self.fetch_trades_by_symbol(symbol)

        metrics = SymbolMetrics(symbol=symbol)
        metrics.calculated_at = datetime.utcnow()

        if not trades:
            logger.warning(f"No trades available for symbol {symbol}")
            return metrics

        # Filter only closed trades
        closed_trades = [t for t in trades if t["exit_time"] is not None]

        if not closed_trades:
            logger.warning(f"No closed trades available for symbol {symbol}")
            return metrics

        metrics.total_trades = len(closed_trades)

        profits = []
        losses = []
        all_returns = []
        hold_times = []

        for trade in closed_trades:
            profit = trade["profit"]
            all_returns.append(profit)

            if profit > 0:
                metrics.winning_trades += 1
                metrics.total_pnl += profit
                profits.append(profit)
            elif profit < 0:
                metrics.losing_trades += 1
                metrics.total_pnl += profit  # Add negative value
                losses.append(profit)

            # Calculate hold time
            if trade["exit_time"]:
                hold_time = (trade["exit_time"] - trade["entry_time"]).total_seconds()
                hold_times.append(hold_time)

        # Calculate win rate
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100

        # Calculate average win/loss
        if profits:
            metrics.average_win = sum(profits) / len(profits)
            metrics.largest_win = max(profits)

        if losses:
            metrics.average_loss = sum(losses) / len(losses)
            metrics.largest_loss = min(losses)

        # Calculate profit factor
        total_profit = sum(profits) if profits else 0
        total_loss = abs(sum(losses)) if losses else 0

        if total_loss > 0:
            metrics.profit_factor = total_profit / total_loss
        elif total_profit > 0:
            metrics.profit_factor = float("inf")

        # Calculate Sharpe ratio (annualized)
        if len(all_returns) > 1:
            returns_array = np.array(all_returns)
            risk_free_rate = 0.05 / 252  # Daily risk-free rate

            excess_returns = returns_array - risk_free_rate
            std_dev = np.std(excess_returns)

            if std_dev > 0:
                metrics.sharpe_ratio = (np.mean(excess_returns) / std_dev) * np.sqrt(252)

        # Calculate average hold time
        if hold_times:
            metrics.avg_hold_time = sum(hold_times) / len(hold_times)

        logger.info(
            f"Symbol metrics calculated for {symbol}: Win Rate={metrics.win_rate:.2f}%, "
            f"Profit Factor={metrics.profit_factor:.2f}, "
            f"Sharpe Ratio={metrics.sharpe_ratio:.2f}, "
            f"Total P&L={metrics.total_pnl:.2f}"
        )

        return metrics

    def calculate_all_symbols(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, SymbolMetrics]:
        """
        Calculate metrics for all symbols in the database.

        Args:
            start_date: Filter trades from this date onwards (optional)
            end_date: Filter trades up to this date (optional)

        Returns:
            Dictionary mapping symbol names to SymbolMetrics objects
        """
        if self._trades_connection is None:
            logger.warning("No trades database connection available")
            return {}

        try:
            # Get all unique symbols
            cursor = self._trades_connection.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM trade_outcomes ORDER BY symbol")
            symbols = [row[0] for row in cursor.fetchall()]

            logger.info(f"Found {len(symbols)} unique symbols: {symbols}")

            # Calculate metrics for each symbol
            all_metrics: dict[str, SymbolMetrics] = {}
            for symbol in symbols:
                trades = self.fetch_trades_by_symbol(symbol, start_date, end_date)
                metrics = self.calculate_symbol_metrics(symbol, trades)
                all_metrics[symbol] = metrics
                self._symbol_metrics[symbol] = metrics

            logger.info(f"Calculated metrics for {len(all_metrics)} symbols")

            return all_metrics

        except sqlite3.Error as e:
            logger.error(f"Failed to calculate all symbols: {e}")
            return {}

    def calculate_symbol_correlation(
        self,
        symbol1: str,
        symbol2: str,
        trades1: Optional[list[dict[str, Any]]] = None,
        trades2: Optional[list[dict[str, Any]]] = None,
    ) -> SymbolCorrelation:
        """
        Calculate correlation between two symbols.

        Args:
            symbol1: First symbol
            symbol2: Second symbol
            trades1: Trades for symbol1 (optional, fetches from DB if None)
            trades2: Trades for symbol2 (optional, fetches from DB if None)

        Returns:
            SymbolCorrelation object with correlation data
        """
        if trades1 is None:
            trades1 = self.fetch_trades_by_symbol(symbol1)

        if trades2 is None:
            trades2 = self.fetch_trades_by_symbol(symbol2)

        correlation = SymbolCorrelation(symbol1=symbol1, symbol2=symbol2)
        correlation.calculated_at = datetime.utcnow()

        # Filter only closed trades
        closed_trades1 = [t for t in trades1 if t["exit_time"] is not None]
        closed_trades2 = [t for t in trades2 if t["exit_time"] is not None]

        if not closed_trades1 or not closed_trades2:
            logger.warning(f"Insufficient data for correlation between {symbol1} and {symbol2}")
            return correlation

        # Create aligned profit series by entry time
        profits1: dict[datetime, float] = {}
        profits2: dict[datetime, float] = {}

        for trade in closed_trades1:
            profits1[trade["entry_time"]] = trade["profit"]

        for trade in closed_trades2:
            profits2[trade["entry_time"]] = trade["profit"]

        # Find common timestamps (trades entered at same time)
        common_times = sorted(set(profits1.keys()) & set(profits2.keys()))

        if len(common_times) < 2:
            logger.warning(
                f"Insufficient aligned data points ({len(common_times)}) for correlation "
                f"between {symbol1} and {symbol2}"
            )
            return correlation

        correlation.sample_size = len(common_times)

        # Build aligned series
        series1 = np.array([profits1[t] for t in common_times])
        series2 = np.array([profits2[t] for t in common_times])

        # Calculate correlation and covariance
        if len(series1) > 1 and len(series2) > 1:
            try:
                correlation_matrix = np.cov(series1, series2)
                correlation.covariance = correlation_matrix[0, 1]

                # Calculate correlation coefficient
                std1 = np.std(series1)
                std2 = np.std(series2)

                if std1 > 0 and std2 > 0:
                    correlation.correlation = correlation.covariance / (std1 * std2)
                else:
                    correlation.correlation = 0.0

            except Exception as e:
                logger.error(f"Failed to calculate correlation: {e}")
                correlation.correlation = 0.0

        logger.info(
            f"Correlation calculated for {symbol1}-{symbol2}: "
            f"{correlation.correlation:.4f} (n={correlation.sample_size})"
        )

        return correlation

    def calculate_correlation_matrix(
        self,
        symbols: Optional[list[str]] = None,
    ) -> dict[tuple[str, str], SymbolCorrelation]:
        """
        Calculate correlation matrix for all symbol pairs.

        Args:
            symbols: List of symbols to analyze. If None, uses all symbols in database.

        Returns:
            Dictionary mapping (symbol1, symbol2) tuples to SymbolCorrelation objects
        """
        if symbols is None:
            if self._trades_connection is None:
                logger.warning("No trades database connection available")
                return {}

            try:
                cursor = self._trades_connection.cursor()
                cursor.execute("SELECT DISTINCT symbol FROM trade_outcomes ORDER BY symbol")
                symbols = [row[0] for row in cursor.fetchall()]
            except sqlite3.Error as e:
                logger.error(f"Failed to fetch symbols: {e}")
                return {}

        logger.info(f"Calculating correlation matrix for {len(symbols)} symbols")

        correlations: dict[tuple[str, str], SymbolCorrelation] = {}

        # Calculate correlation for each unique pair
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                symbol1 = symbols[i]
                symbol2 = symbols[j]

                corr = self.calculate_symbol_correlation(symbol1, symbol2)
                correlations[(symbol1, symbol2)] = corr
                self._correlations[(symbol1, symbol2)] = corr

        logger.info(f"Calculated {len(correlations)} symbol correlations")

        return correlations

    def get_best_performing_symbol(
        self,
        metric: str = "sharpe_ratio",
    ) -> Optional[str]:
        """
        Identify the best performing symbol by a given metric.

        Args:
            metric: Metric to use for ranking ('sharpe_ratio', 'total_pnl', 'win_rate', 'profit_factor')

        Returns:
            Symbol with the best performance, or None if no data available
        """
        if not self._symbol_metrics:
            logger.warning("No symbol metrics available")
            return None

        valid_metrics = ["sharpe_ratio", "total_pnl", "win_rate", "profit_factor"]
        if metric not in valid_metrics:
            logger.warning(f"Invalid metric: {metric}. Valid options: {valid_metrics}")
            return None

        # Find symbol with highest metric value
        best_symbol = max(
            self._symbol_metrics.keys(),
            key=lambda s: getattr(self._symbol_metrics[s], metric, 0)
        )

        best_value = getattr(self._symbol_metrics[best_symbol], metric, 0)

        logger.info(f"Best performing symbol by {metric}: {best_symbol} ({best_value:.4f})")

        return best_symbol

    def get_worst_performing_symbol(
        self,
        metric: str = "sharpe_ratio",
    ) -> Optional[str]:
        """
        Identify the worst performing symbol by a given metric.

        Args:
            metric: Metric to use for ranking ('sharpe_ratio', 'total_pnl', 'win_rate', 'profit_factor')

        Returns:
            Symbol with the worst performance, or None if no data available
        """
        if not self._symbol_metrics:
            logger.warning("No symbol metrics available")
            return None

        valid_metrics = ["sharpe_ratio", "total_pnl", "win_rate", "profit_factor"]
        if metric not in valid_metrics:
            logger.warning(f"Invalid metric: {metric}. Valid options: {valid_metrics}")
            return None

        # Find symbol with lowest metric value
        worst_symbol = min(
            self._symbol_metrics.keys(),
            key=lambda s: getattr(self._symbol_metrics[s], metric, 0)
        )

        worst_value = getattr(self._symbol_metrics[worst_symbol], metric, 0)

        logger.info(f"Worst performing symbol by {metric}: {worst_symbol} ({worst_value:.4f})")

        return worst_symbol

    def get_symbol_ranking(
        self,
        metric: str = "sharpe_ratio",
    ) -> list[SymbolRanking]:
        """
        Generate symbol performance ranking by a given metric.

        Args:
            metric: Metric to use for ranking

        Returns:
            List of SymbolRanking objects sorted by rank (1 = best)
        """
        if not self._symbol_metrics:
            logger.warning("No symbol metrics available")
            return []

        valid_metrics = ["sharpe_ratio", "total_pnl", "win_rate", "profit_factor"]
        if metric not in valid_metrics:
            logger.warning(f"Invalid metric: {metric}. Valid options: {valid_metrics}")
            return []

        # Sort symbols by metric value (descending)
        sorted_symbols = sorted(
            self._symbol_metrics.keys(),
            key=lambda s: getattr(self._symbol_metrics[s], metric, 0),
            reverse=True
        )

        # Create ranking list
        ranking = []
        for rank, symbol in enumerate(sorted_symbols, start=1):
            value = getattr(self._symbol_metrics[symbol], metric, 0)
            ranking.append(
                SymbolRanking(
                    symbol=symbol,
                    rank=rank,
                    metric=metric,
                    value=value,
                )
            )

        logger.info(f"Generated ranking for {len(ranking)} symbols by {metric}")

        return ranking

    def store_symbol_metrics(self, metrics: SymbolMetrics) -> None:
        """
        Store symbol metrics in database.

        Args:
            metrics: SymbolMetrics object to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, metrics not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO symbol_metrics (
                    symbol, win_rate, profit_factor, total_pnl, total_trades,
                    winning_trades, losing_trades, average_win, average_loss,
                    largest_win, largest_loss, sharpe_ratio, avg_hold_time, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.symbol,
                metrics.win_rate,
                metrics.profit_factor if metrics.profit_factor != float("inf") else 999.99,
                metrics.total_pnl,
                metrics.total_trades,
                metrics.winning_trades,
                metrics.losing_trades,
                metrics.average_win,
                metrics.average_loss,
                metrics.largest_win,
                metrics.largest_loss,
                metrics.sharpe_ratio,
                metrics.avg_hold_time,
                metrics.calculated_at.isoformat(),
            ))

            self._connection.commit()

            logger.info(f"Stored metrics for symbol {metrics.symbol}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store symbol metrics: {e}")

    def store_correlation(self, correlation: SymbolCorrelation) -> None:
        """
        Store symbol correlation in database.

        Args:
            correlation: SymbolCorrelation object to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, correlation not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO symbol_correlations (
                    symbol1, symbol2, correlation, covariance, sample_size, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                correlation.symbol1,
                correlation.symbol2,
                correlation.correlation,
                correlation.covariance,
                correlation.sample_size,
                correlation.calculated_at.isoformat(),
            ))

            self._connection.commit()

            logger.info(
                f"Stored correlation for {correlation.symbol1}-{correlation.symbol2}: "
                f"{correlation.correlation:.4f}"
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to store symbol correlation: {e}")

    def store_ranking(self, ranking: list[SymbolRanking]) -> None:
        """
        Store symbol ranking in database.

        Args:
            ranking: List of SymbolRanking objects to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, ranking not stored")
            return

        if not ranking:
            return

        try:
            cursor = self._connection.cursor()

            for rank_item in ranking:
                cursor.execute("""
                    INSERT OR REPLACE INTO symbol_rankings (
                        symbol, rank, metric, value, calculated_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    rank_item.symbol,
                    rank_item.rank,
                    rank_item.metric,
                    rank_item.value,
                    rank_item.calculated_at.isoformat(),
                ))

            self._connection.commit()

            logger.info(f"Stored ranking for {len(ranking)} symbols")

        except sqlite3.Error as e:
            logger.error(f"Failed to store symbol ranking: {e}")

    def generate_performance_report(
        self,
        metric: str = "sharpe_ratio",
    ) -> str:
        """
        Generate a comprehensive symbol performance report.

        Args:
            metric: Primary metric for ranking in the report

        Returns:
            Formatted report string
        """
        if not self._symbol_metrics:
            return "No symbol metrics available for report generation."

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("SYMBOL PERFORMANCE REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        report_lines.append("")

        # Overall statistics
        report_lines.append("OVERVIEW:")
        report_lines.append(f"  Total Symbols Analyzed: {len(self._symbol_metrics)}")
        report_lines.append("")

        # Ranking by primary metric
        ranking = self.get_symbol_ranking(metric=metric)

        report_lines.append(f"RANKING BY {metric.upper().replace('_', ' ')}:")
        report_lines.append("-" * 80)

        for rank_item in ranking:
            metrics = self._symbol_metrics[rank_item.symbol]
            report_lines.append(
                f"  {rank_item.rank:2d}. {rank_item.symbol:6s} - "
                f"{metric}: {rank_item.value:.4f} | "
                f"Win Rate: {metrics.win_rate:.2f}% | "
                f"P&L: {metrics.total_pnl:10.2f} | "
                f"Trades: {metrics.total_trades:3d}"
            )

        report_lines.append("")

        # Best and worst symbols
        best_symbol = self.get_best_performing_symbol(metric)
        worst_symbol = self.get_worst_performing_symbol(metric)

        if best_symbol and worst_symbol:
            best_metrics = self._symbol_metrics[best_symbol]
            worst_metrics = self._symbol_metrics[worst_symbol]

            report_lines.append("BEST AND WORST PERFORMERS:")
            report_lines.append("-" * 80)
            report_lines.append(
                f"  Best ({best_symbol}):  Win Rate={best_metrics.win_rate:.2f}%, "
                f"Sharpe={best_metrics.sharpe_ratio:.4f}, P&L={best_metrics.total_pnl:.2f}"
            )
            report_lines.append(
                f"  Worst ({worst_symbol}): Win Rate={worst_metrics.win_rate:.2f}%, "
                f"Sharpe={worst_metrics.sharpe_ratio:.4f}, P&L={worst_metrics.total_pnl:.2f}"
            )
            report_lines.append("")

        # Correlation analysis
        if self._correlations:
            report_lines.append("SYMBOL CORRELATIONS:")
            report_lines.append("-" * 80)

            # Sort by absolute correlation (highest first)
            sorted_correlations = sorted(
                self._correlations.items(),
                key=lambda x: abs(x[1].correlation),
                reverse=True
            )

            for (symbol1, symbol2), corr in sorted_correlations[:10]:  # Top 10
                report_lines.append(
                    f"  {symbol1}-{symbol2}: {corr.correlation:7.4f} "
                    f"(n={corr.sample_size})"
                )

            report_lines.append("")

        # Detailed metrics table
        report_lines.append("DETAILED METRICS:")
        report_lines.append("-" * 80)
        report_lines.append(
            f"{'Symbol':<8} {'Win Rate':>10} {'Profit Factor':>14} {'Sharpe':>10} "
            f"{'Total P&L':>12} {'Trades':>8}"
        )
        report_lines.append("-" * 80)

        for symbol in sorted(self._symbol_metrics.keys()):
            metrics = self._symbol_metrics[symbol]
            report_lines.append(
                f"{symbol:<8} "
                f"{metrics.win_rate:>9.2f}% "
                f"{metrics.profit_factor:>13.2f} "
                f"{metrics.sharpe_ratio:>10.4f} "
                f"{metrics.total_pnl:>12.2f} "
                f"{metrics.total_trades:>8d}"
            )

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def analyze_all_symbols(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        calculate_correlations: bool = True,
        store_results: bool = True,
    ) -> dict[str, SymbolMetrics]:
        """
        Perform complete symbol performance analysis.

        This is the main entry point for symbol analysis. It:
        1. Calculates metrics for all symbols
        2. Calculates correlation matrix (optional)
        3. Stores results in database (optional)

        Args:
            start_date: Filter trades from this date onwards (optional)
            end_date: Filter trades up to this date (optional)
            calculate_correlations: Whether to calculate symbol correlations
            store_results: Whether to store results in database

        Returns:
            Dictionary mapping symbol names to SymbolMetrics objects
        """
        logger.info("Starting comprehensive symbol performance analysis")

        # Calculate all symbol metrics
        all_metrics = self.calculate_all_symbols(start_date, end_date)

        if not all_metrics:
            logger.warning("No symbols found for analysis")
            return {}

        # Calculate correlations if requested
        if calculate_correlations:
            logger.info("Calculating symbol correlation matrix")
            self.calculate_correlation_matrix(symbols=list(all_metrics.keys()))

        # Store results if requested
        if store_results:
            logger.info("Storing analysis results in database")

            # Store metrics for each symbol
            for symbol, metrics in all_metrics.items():
                self.store_symbol_metrics(metrics)

            # Store correlations
            for correlation in self._correlations.values():
                self.store_correlation(correlation)

            # Store rankings for multiple metrics
            for metric in ["sharpe_ratio", "total_pnl", "win_rate", "profit_factor"]:
                ranking = self.get_symbol_ranking(metric=metric)
                self.store_ranking(ranking)

        logger.info(
            f"Symbol performance analysis completed: "
            f"{len(all_metrics)} symbols analyzed"
        )

        return all_metrics

    def get_symbol_metrics(self, symbol: str) -> Optional[SymbolMetrics]:
        """
        Get cached metrics for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            SymbolMetrics object or None if not available
        """
        return self._symbol_metrics.get(symbol)

    def get_symbol_correlation(
        self,
        symbol1: str,
        symbol2: str,
    ) -> Optional[SymbolCorrelation]:
        """
        Get cached correlation between two symbols.

        Args:
            symbol1: First symbol
            symbol2: Second symbol

        Returns:
            SymbolCorrelation object or None if not available
        """
        # Try both orderings
        key = (symbol1, symbol2) if symbol1 < symbol2 else (symbol2, symbol1)
        return self._correlations.get(key)

    def get_historical_symbol_metrics(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get historical metrics for a specific symbol from database.

        Args:
            symbol: Trading symbol
            limit: Maximum number of records to return

        Returns:
            List of metric dictionaries
        """
        if self._connection is None:
            logger.warning("Database connection not available")
            return []

        try:
            cursor = self._connection.cursor()

            query = """
                SELECT * FROM symbol_metrics
                WHERE symbol = ?
                ORDER BY calculated_at DESC
                LIMIT ?
            """
            cursor.execute(query, (symbol, limit))

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            logger.info(f"Retrieved {len(results)} historical metrics for {symbol}")

            return results

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve historical symbol metrics: {e}")
            return []

    def close(self) -> None:
        """Close database connections."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

        if self._trades_connection is not None:
            self._trades_connection.close()
            self._trades_connection = None

        logger.info("Database connections closed")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        self.close()
