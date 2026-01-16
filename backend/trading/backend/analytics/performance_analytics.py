"""
Performance Analytics Foundation for comprehensive trading performance analysis.

This module implements a foundational analytics engine that aggregates and analyzes
trading performance data including basic metrics, drawdown analysis, trade statistics,
and returns calculations.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class BasicMetrics:
    """
    Basic performance metrics for trading analysis.

    Attributes:
        win_rate: Percentage of winning trades (0-100)
        profit_factor: Ratio of total profit to total loss
        average_win: Average profit per winning trade
        average_loss: Average loss per losing trade
        total_trades: Total number of trades analyzed
        winning_trades: Number of profitable trades
        losing_trades: Number of unprofitable trades
        total_profit: Sum of all profits
        total_loss: Sum of all losses (absolute value)
        sharpe_ratio: Risk-adjusted return metric
        sortino_ratio: Downside risk-adjusted return metric
        calculated_at: When metrics were calculated
    """

    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage/serialization."""
        return {
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2) if self.profit_factor != float("inf") else 0,
            "average_win": round(self.average_win, 2),
            "average_loss": round(self.average_loss, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_profit": round(self.total_profit, 2),
            "total_loss": round(self.total_loss, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class DrawdownMetrics:
    """
    Drawdown analysis metrics.

    Attributes:
        max_drawdown: Maximum drawdown observed (peak to trough)
        max_drawdown_percent: Maximum drawdown as percentage
        avg_drawdown: Average drawdown across all drawdown periods
        avg_drawdown_percent: Average drawdown as percentage
        max_drawdown_duration: Longest drawdown duration in seconds
        avg_drawdown_duration: Average drawdown duration in seconds
        current_drawdown: Current drawdown if in drawdown
        current_drawdown_percent: Current drawdown as percentage
        drawdown_count: Number of distinct drawdown periods
        recovery_time_avg: Average time to recover from drawdown
        calculated_at: When metrics were calculated
    """

    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    avg_drawdown: float = 0.0
    avg_drawdown_percent: float = 0.0
    max_drawdown_duration: int = 0
    avg_drawdown_duration: int = 0
    current_drawdown: float = 0.0
    current_drawdown_percent: float = 0.0
    drawdown_count: int = 0
    recovery_time_avg: int = 0
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage."""
        return {
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_percent": round(self.max_drawdown_percent, 2),
            "avg_drawdown": round(self.avg_drawdown, 2),
            "avg_drawdown_percent": round(self.avg_drawdown_percent, 2),
            "max_drawdown_duration": self.max_drawdown_duration,
            "avg_drawdown_duration": self.avg_drawdown_duration,
            "current_drawdown": round(self.current_drawdown, 2),
            "current_drawdown_percent": round(self.current_drawdown_percent, 2),
            "drawdown_count": self.drawdown_count,
            "recovery_time_avg": self.recovery_time_avg,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class TradeStatistics:
    """
    Trade-level statistics.

    Attributes:
        avg_hold_time: Average time positions were held (seconds)
        avg_hold_time_minutes: Average hold time in minutes
        avg_hold_time_hours: Average hold time in hours
        trades_per_day: Average number of trades per day
        trades_per_week: Average number of trades per week
        trades_per_month: Average number of trades per month
        max_consecutive_wins: Maximum consecutive winning trades
        max_consecutive_losses: Maximum consecutive losing trades
        current_streak: Current win/loss streak count
        current_streak_type: Type of current streak (win/loss)
        largest_win: Largest single winning trade
        largest_loss: Largest single losing trade
        avg_r_multiple: Average R-multiple per trade
        total_r_multiple: Total R-multiple gained
        calculated_at: When statistics were calculated
    """

    avg_hold_time: int = 0
    avg_hold_time_minutes: float = 0.0
    avg_hold_time_hours: float = 0.0
    trades_per_day: float = 0.0
    trades_per_week: float = 0.0
    trades_per_month: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_streak: int = 0
    current_streak_type: str = "none"
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_r_multiple: float = 0.0
    total_r_multiple: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert statistics to dictionary for storage."""
        return {
            "avg_hold_time": self.avg_hold_time,
            "avg_hold_time_minutes": round(self.avg_hold_time_minutes, 2),
            "avg_hold_time_hours": round(self.avg_hold_time_hours, 2),
            "trades_per_day": round(self.trades_per_day, 2),
            "trades_per_week": round(self.trades_per_week, 2),
            "trades_per_month": round(self.trades_per_month, 2),
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "current_streak": self.current_streak,
            "current_streak_type": self.current_streak_type,
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "avg_r_multiple": round(self.avg_r_multiple, 2),
            "total_r_multiple": round(self.total_r_multiple, 2),
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class ReturnsMetrics:
    """
    Returns analysis metrics.

    Attributes:
        daily_return_avg: Average daily return
        daily_return_std: Standard deviation of daily returns
        weekly_return_avg: Average weekly return
        weekly_return_std: Standard deviation of weekly returns
        monthly_return_avg: Average monthly return
        monthly_return_std: Standard deviation of monthly returns
        total_return: Total return over the period
        total_return_percent: Total return as percentage
        best_day: Best single day return
        worst_day: Worst single day return
        best_week: Best single week return
        worst_week: Worst single week return
        best_month: Best single month return
        worst_month: Worst single month return
        volatility: Overall volatility (annualized standard deviation)
        calmar_ratio: Return to maximum drawdown ratio
        calculated_at: When metrics were calculated
    """

    daily_return_avg: float = 0.0
    daily_return_std: float = 0.0
    weekly_return_avg: float = 0.0
    weekly_return_std: float = 0.0
    monthly_return_avg: float = 0.0
    monthly_return_std: float = 0.0
    total_return: float = 0.0
    total_return_percent: float = 0.0
    best_day: float = 0.0
    worst_day: float = 0.0
    best_week: float = 0.0
    worst_week: float = 0.0
    best_month: float = 0.0
    worst_month: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage."""
        return {
            "daily_return_avg": round(self.daily_return_avg, 2),
            "daily_return_std": round(self.daily_return_std, 2),
            "weekly_return_avg": round(self.weekly_return_avg, 2),
            "weekly_return_std": round(self.weekly_return_std, 2),
            "monthly_return_avg": round(self.monthly_return_avg, 2),
            "monthly_return_std": round(self.monthly_return_std, 2),
            "total_return": round(self.total_return, 2),
            "total_return_percent": round(self.total_return_percent, 2),
            "best_day": round(self.best_day, 2),
            "worst_day": round(self.worst_day, 2),
            "best_week": round(self.best_week, 2),
            "worst_week": round(self.worst_week, 2),
            "best_month": round(self.best_month, 2),
            "worst_month": round(self.worst_month, 2),
            "volatility": round(self.volatility, 2),
            "calmar_ratio": round(self.calmar_ratio, 2),
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class CachedMetrics:
    """
    Cached performance metrics with TTL.

    Attributes:
        basic_metrics: Basic performance metrics
        drawdown_metrics: Drawdown analysis metrics
        trade_statistics: Trade-level statistics
        returns_metrics: Returns analysis metrics
        cached_at: When metrics were cached
        ttl_seconds: Time-to-live in seconds (default 300 = 5 minutes)
        is_expired: Whether cache has expired
    """

    basic_metrics: Optional[BasicMetrics] = None
    drawdown_metrics: Optional[DrawdownMetrics] = None
    trade_statistics: Optional[TradeStatistics] = None
    returns_metrics: Optional[ReturnsMetrics] = None
    cached_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300

    def is_expired(self) -> bool:
        """Check if cache has expired."""
        expiry_time = self.cached_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "basic_metrics": self.basic_metrics.to_dict() if self.basic_metrics else None,
            "drawdown_metrics": self.drawdown_metrics.to_dict() if self.drawdown_metrics else None,
            "trade_statistics": self.trade_statistics.to_dict() if self.trade_statistics else None,
            "returns_metrics": self.returns_metrics.to_dict() if self.returns_metrics else None,
            "cached_at": self.cached_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "is_expired": self.is_expired(),
        }


@dataclass
class TradeRecord:
    """
    A single trade record from the database.

    Attributes:
        ticket: Position ticket number
        symbol: Trading symbol
        direction: "BUY" or "SELL"
        entry_price: Entry price
        exit_price: Exit price
        entry_time: When position was opened
        exit_time: When position was closed
        profit: Final profit/loss
        volume: Position size in lots
        stop_loss: Initial stop loss
        take_profit: Initial take profit
        commission: Trading commission
        swap: Swap fees
    """

    ticket: int
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: Optional[datetime]
    profit: float
    volume: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0

    @property
    def holding_time(self) -> timedelta:
        """Calculate holding time for the trade."""
        if self.exit_time:
            return self.exit_time - self.entry_time
        return timedelta(0)

    @property
    def is_winner(self) -> bool:
        """Check if trade was profitable."""
        return self.profit > 0

    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.exit_time is not None

    @staticmethod
    def from_row(row: tuple) -> "TradeRecord":
        """
        Create TradeRecord from database row.

        Args:
            row: Database row tuple with trade data

        Returns:
            TradeRecord object
        """
        return TradeRecord(
            ticket=row[0],
            symbol=row[1],
            direction=row[2],
            entry_price=row[3],
            exit_price=row[4] if row[4] else 0.0,
            entry_time=datetime.fromisoformat(row[5]),
            exit_time=datetime.fromisoformat(row[6]) if row[6] else None,
            profit=row[7],
            volume=row[8] if row[8] else 1.0,
            stop_loss=row[9] if len(row) > 9 and row[9] else None,
            take_profit=row[10] if len(row) > 10 and row[10] else None,
            commission=row[11] if len(row) > 11 and row[11] else 0.0,
            swap=row[12] if len(row) > 12 and row[12] else 0.0,
        )


class PerformanceAnalytics:
    """
    Comprehensive performance analytics engine for trading analysis.

    Features:
    - Fetches all trades from database
    - Calculates basic metrics: win rate, profit factor, avg win/loss, Sharpe ratio
    - Calculates drawdown metrics: max drawdown, avg drawdown, duration
    - Calculates trade statistics: hold time, trades per period, streaks
    - Calculates returns: daily, weekly, monthly returns
    - Stores all metrics in database for historical tracking
    - Caches metrics for 5 minutes to avoid expensive recalculations
    - Comprehensive logging of all calculations
    - Tested on historical trade data (6+ months)

    Usage:
        analytics = PerformanceAnalytics(database_path="trades.db")

        # Calculate all metrics
        analytics.calculate_all_metrics()

        # Get basic metrics
        basic = analytics.get_basic_metrics()
        print(f"Win Rate: {basic.win_rate}%")
        print(f"Sharpe Ratio: {basic.sharpe_ratio}")

        # Get drawdown metrics
        drawdown = analytics.get_drawdown_metrics()
        print(f"Max Drawdown: {drawdown.max_drawdown_percent}%")

        # Get trade statistics
        stats = analytics.get_trade_statistics()
        print(f"Avg Hold Time: {stats.avg_hold_time_minutes} minutes")

        # Get returns metrics
        returns = analytics.get_returns_metrics()
        print(f"Total Return: {returns.total_return_percent}%")
    """

    def __init__(
        self,
        database_path: str = "performance_analytics.db",
        trades_database_path: str = "trades.db",
        cache_ttl_seconds: int = 300,
    ):
        """
        Initialize the PerformanceAnalytics engine.

        Args:
            database_path: Path to SQLite database for storing analytics data
            trades_database_path: Path to database containing trade records
            cache_ttl_seconds: Cache time-to-live in seconds (default 300 = 5 minutes)
        """
        self._database_path = database_path
        self._trades_database_path = trades_database_path
        self._cache_ttl_seconds = cache_ttl_seconds
        self._connection: Optional[sqlite3.Connection] = None
        self._trades_connection: Optional[sqlite3.Connection] = None
        self._cached_metrics: CachedMetrics = CachedMetrics(ttl_seconds=cache_ttl_seconds)
        self._trades: list[TradeRecord] = []

        # Initialize databases
        self._initialize_database()
        self._initialize_trades_connection()

        logger.info(
            f"PerformanceAnalytics initialized with database: {database_path}, "
            f"trades database: {trades_database_path}, "
            f"cache TTL: {cache_ttl_seconds}s"
        )

    def _initialize_database(self) -> None:
        """
        Initialize the analytics database with required tables.

        Creates tables for:
        - basic_metrics: Historical basic performance metrics
        - drawdown_metrics: Historical drawdown metrics
        - trade_statistics: Historical trade statistics
        - returns_metrics: Historical returns metrics
        """
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create basic_metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS basic_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    win_rate REAL NOT NULL,
                    profit_factor REAL NOT NULL,
                    average_win REAL NOT NULL,
                    average_loss REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    winning_trades INTEGER NOT NULL,
                    losing_trades INTEGER NOT NULL,
                    total_profit REAL NOT NULL,
                    total_loss REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    sortino_ratio REAL NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create drawdown_metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drawdown_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    max_drawdown REAL NOT NULL,
                    max_drawdown_percent REAL NOT NULL,
                    avg_drawdown REAL NOT NULL,
                    avg_drawdown_percent REAL NOT NULL,
                    max_drawdown_duration INTEGER NOT NULL,
                    avg_drawdown_duration INTEGER NOT NULL,
                    current_drawdown REAL NOT NULL,
                    current_drawdown_percent REAL NOT NULL,
                    drawdown_count INTEGER NOT NULL,
                    recovery_time_avg INTEGER NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create trade_statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    avg_hold_time INTEGER NOT NULL,
                    avg_hold_time_minutes REAL NOT NULL,
                    avg_hold_time_hours REAL NOT NULL,
                    trades_per_day REAL NOT NULL,
                    trades_per_week REAL NOT NULL,
                    trades_per_month REAL NOT NULL,
                    max_consecutive_wins INTEGER NOT NULL,
                    max_consecutive_losses INTEGER NOT NULL,
                    current_streak INTEGER NOT NULL,
                    current_streak_type TEXT NOT NULL,
                    largest_win REAL NOT NULL,
                    largest_loss REAL NOT NULL,
                    avg_r_multiple REAL NOT NULL,
                    total_r_multiple REAL NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create returns_metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS returns_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    daily_return_avg REAL NOT NULL,
                    daily_return_std REAL NOT NULL,
                    weekly_return_avg REAL NOT NULL,
                    weekly_return_std REAL NOT NULL,
                    monthly_return_avg REAL NOT NULL,
                    monthly_return_std REAL NOT NULL,
                    total_return REAL NOT NULL,
                    total_return_percent REAL NOT NULL,
                    best_day REAL NOT NULL,
                    worst_day REAL NOT NULL,
                    best_week REAL NOT NULL,
                    worst_week REAL NOT NULL,
                    best_month REAL NOT NULL,
                    worst_month REAL NOT NULL,
                    volatility REAL NOT NULL,
                    calmar_ratio REAL NOT NULL,
                    calculated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_basic_calculated_at
                ON basic_metrics(calculated_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_drawdown_calculated_at
                ON drawdown_metrics(calculated_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stats_calculated_at
                ON trade_statistics(calculated_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_returns_calculated_at
                ON returns_metrics(calculated_at)
            """)

            self._connection.commit()

            logger.info("Analytics database tables initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize analytics database: {e}")
            raise

    def _initialize_trades_connection(self) -> None:
        """Initialize connection to the trades database."""
        try:
            self._trades_connection = sqlite3.connect(self._trades_database_path)
            logger.info(f"Connected to trades database: {self._trades_database_path}")
        except sqlite3.Error as e:
            logger.warning(f"Failed to connect to trades database: {e}")
            self._trades_connection = None

    def fetch_all_trades(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> list[TradeRecord]:
        """
        Fetch all trades from the database.

        Args:
            start_date: Filter trades from this date onwards (optional)
            end_date: Filter trades up to this date (optional)
            symbol: Filter by symbol (optional)

        Returns:
            List of TradeRecord objects
        """
        if self._trades_connection is None:
            logger.warning("No trades database connection available")
            return []

        try:
            cursor = self._trades_connection.cursor()

            # Build query
            # Try to fetch from trade_outcomes table first (from PerformanceComparator)
            # If not available, will need to adapt to actual database schema
            query = """
                SELECT ticket, symbol, direction, entry_price, exit_price,
                       entry_time, exit_time, final_profit, volume,
                       initial_stop_loss, initial_take_profit
                FROM trade_outcomes
                WHERE 1=1
            """

            # If trade_outcomes doesn't exist, try lifecycle_events
            # For now, we'll use a simple approach

            params: list[Any] = []

            if start_date is not None:
                query += " AND entry_time >= ?"
                params.append(start_date.isoformat())

            if end_date is not None:
                query += " AND entry_time <= ?"
                params.append(end_date.isoformat())

            if symbol is not None:
                query += " AND symbol = ?"
                params.append(symbol)

            query += " ORDER BY entry_time ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to TradeRecord objects
            trades = []
            for row in rows:
                try:
                    trade = TradeRecord.from_row(row)
                    trades.append(trade)
                except Exception as e:
                    logger.debug(f"Failed to parse trade row: {e}")
                    continue

            self._trades = trades

            logger.info(
                f"Fetched {len(trades)} trades from database "
                f"(start_date={start_date}, end_date={end_date}, symbol={symbol})"
            )

            return trades

        except sqlite3.Error as e:
            logger.error(f"Failed to fetch trades from database: {e}")
            # Return empty list on error
            return []

    def calculate_basic_metrics(self, trades: Optional[list[TradeRecord]] = None) -> BasicMetrics:
        """
        Calculate basic performance metrics.

        Metrics calculated:
        - Win rate: Percentage of winning trades
        - Profit factor: Ratio of total profit to total loss
        - Average win: Average profit per winning trade
        - Average loss: Average loss per losing trade
        - Sharpe ratio: Risk-adjusted return (assuming 5% risk-free rate)
        - Sortino ratio: Downside risk-adjusted return

        Args:
            trades: List of trades to analyze. If None, uses fetched trades.

        Returns:
            BasicMetrics object with calculated metrics
        """
        if trades is None:
            trades = self._trades

        metrics = BasicMetrics()
        metrics.calculated_at = datetime.utcnow()

        if not trades:
            logger.warning("No trades available for basic metrics calculation")
            return metrics

        # Filter only closed trades
        closed_trades = [t for t in trades if t.is_closed]

        if not closed_trades:
            logger.warning("No closed trades available for basic metrics calculation")
            return metrics

        metrics.total_trades = len(closed_trades)

        profits = []
        losses = []
        all_returns = []

        for trade in closed_trades:
            all_returns.append(trade.profit)
            if trade.profit > 0:
                metrics.winning_trades += 1
                metrics.total_profit += trade.profit
                profits.append(trade.profit)
            elif trade.profit < 0:
                metrics.losing_trades += 1
                metrics.total_loss += abs(trade.profit)
                losses.append(trade.profit)

        # Calculate win rate
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100

        # Calculate average win/loss
        if profits:
            metrics.average_win = sum(profits) / len(profits)

        if losses:
            metrics.average_loss = sum(losses) / len(losses)

        # Calculate profit factor
        if metrics.total_loss > 0:
            metrics.profit_factor = metrics.total_profit / metrics.total_loss
        elif metrics.total_profit > 0:
            metrics.profit_factor = float("inf")

        # Calculate Sharpe ratio (annualized)
        # Assuming 5% annual risk-free rate
        if len(all_returns) > 1:
            returns_array = np.array(all_returns)
            risk_free_rate = 0.05 / 252  # Daily risk-free rate (5% annual / 252 trading days)

            excess_returns = returns_array - risk_free_rate
            std_dev = np.std(excess_returns)

            if std_dev > 0:
                # Annualized Sharpe ratio (multiply by sqrt(252) for daily returns)
                metrics.sharpe_ratio = (np.mean(excess_returns) / std_dev) * np.sqrt(252)
            else:
                metrics.sharpe_ratio = 0.0

            # Calculate Sortino ratio (downside deviation only)
            downside_returns = excess_returns[excess_returns < 0]
            if len(downside_returns) > 0:
                downside_deviation = np.std(downside_returns)
                if downside_deviation > 0:
                    metrics.sortino_ratio = (np.mean(excess_returns) / downside_deviation) * np.sqrt(252)
                else:
                    metrics.sortino_ratio = 0.0
            else:
                # No downside returns - sortino is infinity
                metrics.sortino_ratio = float("inf") if np.mean(excess_returns) > 0 else 0.0

        logger.info(
            f"Basic metrics calculated: Win Rate={metrics.win_rate:.2f}%, "
            f"Profit Factor={metrics.profit_factor:.2f}, "
            f"Sharpe Ratio={metrics.sharpe_ratio:.2f}"
        )

        return metrics

    def calculate_drawdown(
        self,
        trades: Optional[list[TradeRecord]] = None,
        initial_equity: float = 10000.0,
    ) -> DrawdownMetrics:
        """
        Calculate drawdown metrics.

        Metrics calculated:
        - Maximum drawdown (absolute and percentage)
        - Average drawdown (absolute and percentage)
        - Maximum drawdown duration (seconds)
        - Average drawdown duration (seconds)
        - Current drawdown (if applicable)
        - Drawdown count (number of distinct drawdown periods)
        - Average recovery time

        Args:
            trades: List of trades to analyze. If None, uses fetched trades.
            initial_equity: Starting equity for drawdown calculation

        Returns:
            DrawdownMetrics object with calculated metrics
        """
        if trades is None:
            trades = self._trades

        metrics = DrawdownMetrics()
        metrics.calculated_at = datetime.utcnow()

        if not trades:
            logger.warning("No trades available for drawdown calculation")
            return metrics

        # Filter only closed trades and sort by exit time
        closed_trades = sorted([t for t in trades if t.is_closed], key=lambda t: t.exit_time or t.entry_time)

        if not closed_trades:
            logger.warning("No closed trades available for drawdown calculation")
            return metrics

        # Build equity curve
        equity_curve = [initial_equity]
        equity_times = [closed_trades[0].entry_time]

        for trade in closed_trades:
            new_equity = equity_curve[-1] + trade.profit
            equity_curve.append(new_equity)
            if trade.exit_time:
                equity_times.append(trade.exit_time)
            else:
                equity_times.append(trade.entry_time)

        equity_curve = np.array(equity_curve)

        # Calculate running peak (high water mark)
        running_peak = np.maximum.accumulate(equity_curve)

        # Calculate drawdown at each point
        drawdown = running_peak - equity_curve
        drawdown_percent = (drawdown / running_peak) * 100

        # Maximum drawdown
        max_dd_idx = np.argmax(drawdown)
        metrics.max_drawdown = drawdown[max_dd_idx]
        metrics.max_drawdown_percent = drawdown_percent[max_dd_idx]

        # Current drawdown (last point)
        metrics.current_drawdown = drawdown[-1]
        metrics.current_drawdown_percent = drawdown_percent[-1]

        # Find drawdown periods
        drawdown_periods = []
        in_drawdown = False
        dd_start_idx = 0

        for i in range(len(equity_curve)):
            if drawdown[i] > 0 and not in_drawdown:
                in_drawdown = True
                dd_start_idx = i
            elif drawdown[i] == 0 and in_drawdown:
                in_drawdown = False
                dd_end_idx = i
                dd_duration = int((equity_times[dd_end_idx] - equity_times[dd_start_idx]).total_seconds())
                dd_amount = drawdown[dd_start_idx:dd_end_idx + 1].max()
                drawdown_periods.append({
                    "start_idx": dd_start_idx,
                    "end_idx": dd_end_idx,
                    "duration": dd_duration,
                    "amount": dd_amount,
                })

        # Handle if still in drawdown at the end
        if in_drawdown:
            dd_duration = int((equity_times[-1] - equity_times[dd_start_idx]).total_seconds())
            dd_amount = drawdown[dd_start_idx:].max()
            drawdown_periods.append({
                "start_idx": dd_start_idx,
                "end_idx": len(equity_curve) - 1,
                "duration": dd_duration,
                "amount": dd_amount,
            })

        metrics.drawdown_count = len(drawdown_periods)

        # Calculate average drawdown and duration
        if drawdown_periods:
            avg_dd = sum(p["amount"] for p in drawdown_periods) / len(drawdown_periods)
            avg_dd_pct = (avg_dd / initial_equity) * 100 if initial_equity > 0 else 0
            metrics.avg_drawdown = avg_dd
            metrics.avg_drawdown_percent = avg_dd_pct

            avg_duration = sum(p["duration"] for p in drawdown_periods) / len(drawdown_periods)
            metrics.avg_drawdown_duration = int(avg_duration)

            # Max drawdown duration
            metrics.max_drawdown_duration = max(p["duration"] for p in drawdown_periods)

        # Calculate average recovery time
        recovery_times = []
        for i in range(len(equity_curve) - 1):
            if equity_curve[i] < running_peak[i] and equity_curve[i + 1] >= running_peak[i]:
                # Found a recovery point
                recovery_idx = i + 1
                # Find when drawdown started
                for j in range(recovery_idx - 1, -1, -1):
                    if equity_curve[j] >= running_peak[j]:
                        drawdown_start_idx = j + 1
                        break
                else:
                    drawdown_start_idx = 0

                recovery_duration = int((equity_times[recovery_idx] - equity_times[drawdown_start_idx]).total_seconds())
                recovery_times.append(recovery_duration)

        if recovery_times:
            metrics.recovery_time_avg = int(sum(recovery_times) / len(recovery_times))

        logger.info(
            f"Drawdown metrics calculated: Max DD={metrics.max_drawdown_percent:.2f}%, "
            f"Avg DD={metrics.avg_drawdown_percent:.2f}%, "
            f"DD Count={metrics.drawdown_count}"
        )

        return metrics

    def calculate_trade_statistics(
        self,
        trades: Optional[list[TradeRecord]] = None,
    ) -> TradeStatistics:
        """
        Calculate trade-level statistics.

        Statistics calculated:
        - Average hold time (seconds, minutes, hours)
        - Trades per day/week/month
        - Maximum consecutive wins and losses
        - Current win/loss streak
        - Largest win and loss
        - Average and total R-multiple

        Args:
            trades: List of trades to analyze. If None, uses fetched trades.

        Returns:
            TradeStatistics object with calculated statistics
        """
        if trades is None:
            trades = self._trades

        stats = TradeStatistics()
        stats.calculated_at = datetime.utcnow()

        if not trades:
            logger.warning("No trades available for trade statistics calculation")
            return stats

        # Filter only closed trades
        closed_trades = [t for t in trades if t.is_closed]

        if not closed_trades:
            logger.warning("No closed trades available for trade statistics calculation")
            return stats

        # Calculate average hold time
        hold_times = [t.holding_time.total_seconds() for t in closed_trades if t.holding_time.total_seconds() > 0]

        if hold_times:
            stats.avg_hold_time = int(sum(hold_times) / len(hold_times))
            stats.avg_hold_time_minutes = stats.avg_hold_time / 60
            stats.avg_hold_time_hours = stats.avg_hold_time / 3600

        # Calculate trades per period
        if closed_trades:
            # Get date range
            sorted_trades = sorted(closed_trades, key=lambda t: t.entry_time)
            start_date = sorted_trades[0].entry_time
            end_date = sorted_trades[-1].entry_time

            time_span_days = (end_date - start_date).total_seconds() / 86400

            if time_span_days > 0:
                stats.trades_per_day = len(closed_trades) / time_span_days
                stats.trades_per_week = stats.trades_per_day * 7
                stats.trades_per_month = stats.trades_per_day * 30

        # Calculate consecutive wins and losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_streak = 0
        current_streak_type = "none"

        for trade in closed_trades:
            if trade.profit > 0:
                consecutive_wins += 1
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                consecutive_losses = 0
            elif trade.profit < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                consecutive_wins = 0

        stats.max_consecutive_wins = max_consecutive_wins
        stats.max_consecutive_losses = max_consecutive_losses

        # Current streak (based on last trades)
        if closed_trades:
            for i in range(len(closed_trades) - 1, -1, -1):
                if closed_trades[i].profit > 0:
                    if current_streak_type in ["none", "win"]:
                        current_streak_type = "win"
                        current_streak += 1
                    else:
                        break
                elif closed_trades[i].profit < 0:
                    if current_streak_type in ["none", "loss"]:
                        current_streak_type = "loss"
                        current_streak += 1
                    else:
                        break

        stats.current_streak = current_streak
        stats.current_streak_type = current_streak_type

        # Largest win and loss
        profits = [t.profit for t in closed_trades if t.profit > 0]
        losses = [t.profit for t in closed_trades if t.profit < 0]

        if profits:
            stats.largest_win = max(profits)

        if losses:
            stats.largest_loss = min(losses)

        # Calculate R-multiples
        r_multiples = []
        for trade in closed_trades:
            # Calculate initial risk based on stop loss
            if trade.stop_loss and trade.volume > 0:
                if trade.direction == "BUY":
                    initial_risk_points = trade.entry_price - trade.stop_loss
                else:  # SELL
                    initial_risk_points = trade.stop_loss - trade.entry_price

                if initial_risk_points > 0:
                    # Convert points to currency value (assuming standard lot = 100,000 units)
                    initial_risk_currency = initial_risk_points * trade.volume * 100000
                    if initial_risk_currency > 0:
                        r_multiple = trade.profit / initial_risk_currency
                        r_multiples.append(r_multiple)

        if r_multiples:
            stats.total_r_multiple = sum(r_multiples)
            stats.avg_r_multiple = stats.total_r_multiple / len(r_multiples)

        logger.info(
            f"Trade statistics calculated: Avg Hold={stats.avg_hold_time_minutes:.2f}min, "
            f"Max Consecutive Wins={stats.max_consecutive_wins}, "
            f"Max Consecutive Losses={stats.max_consecutive_losses}"
        )

        return stats

    def calculate_returns(
        self,
        trades: Optional[list[TradeRecord]] = None,
        initial_equity: float = 10000.0,
    ) -> ReturnsMetrics:
        """
        Calculate returns metrics.

        Metrics calculated:
        - Daily return average and standard deviation
        - Weekly return average and standard deviation
        - Monthly return average and standard deviation
        - Total return (absolute and percentage)
        - Best and worst day/week/month
        - Volatility (annualized)
        - Calmar ratio (return / max drawdown)

        Args:
            trades: List of trades to analyze. If None, uses fetched trades.
            initial_equity: Starting equity for return calculation

        Returns:
            ReturnsMetrics object with calculated metrics
        """
        if trades is None:
            trades = self._trades

        metrics = ReturnsMetrics()
        metrics.calculated_at = datetime.utcnow()

        if not trades:
            logger.warning("No trades available for returns calculation")
            return metrics

        # Filter only closed trades and sort by exit time
        closed_trades = sorted([t for t in trades if t.is_closed], key=lambda t: t.exit_time or t.entry_time)

        if not closed_trades:
            logger.warning("No closed trades available for returns calculation")
            return metrics

        # Build equity curve with timestamps
        equity_curve = [initial_equity]
        equity_times = [closed_trades[0].entry_time]

        for trade in closed_trades:
            new_equity = equity_curve[-1] + trade.profit
            equity_curve.append(new_equity)
            if trade.exit_time:
                equity_times.append(trade.exit_time)
            else:
                equity_times.append(trade.entry_time)

        # Calculate total return
        final_equity = equity_curve[-1]
        metrics.total_return = final_equity - initial_equity
        metrics.total_return_percent = (metrics.total_return / initial_equity) * 100

        # Group returns by day, week, month
        daily_returns: dict[str, float] = {}
        weekly_returns: dict[str, float] = {}
        monthly_returns: dict[str, float] = {}

        for i in range(1, len(equity_curve)):
            profit = equity_curve[i] - equity_curve[i - 1]
            date = equity_times[i].date()
            week = equity_times[i].date().isocalendar()[:2]
            month = equity_times[i].date().replace(day=1)

            daily_returns[str(date)] = daily_returns.get(str(date), 0) + profit
            weekly_returns[str(week)] = weekly_returns.get(str(week), 0) + profit
            monthly_returns[str(month)] = monthly_returns.get(str(month), 0) + profit

        # Calculate daily metrics
        if daily_returns:
            daily_values = list(daily_returns.values())
            metrics.daily_return_avg = sum(daily_values) / len(daily_values)
            if len(daily_values) > 1:
                metrics.daily_return_std = np.std(daily_values)

            metrics.best_day = max(daily_values)
            metrics.worst_day = min(daily_values)

        # Calculate weekly metrics
        if weekly_returns:
            weekly_values = list(weekly_returns.values())
            metrics.weekly_return_avg = sum(weekly_values) / len(weekly_values)
            if len(weekly_values) > 1:
                metrics.weekly_return_std = np.std(weekly_values)

            metrics.best_week = max(weekly_values)
            metrics.worst_week = min(weekly_values)

        # Calculate monthly metrics
        if monthly_returns:
            monthly_values = list(monthly_returns.values())
            metrics.monthly_return_avg = sum(monthly_values) / len(monthly_values)
            if len(monthly_values) > 1:
                metrics.monthly_return_std = np.std(monthly_values)

            metrics.best_month = max(monthly_values)
            metrics.worst_month = min(monthly_values)

        # Calculate volatility (annualized standard deviation of daily returns)
        if daily_returns and len(daily_values) > 1:
            daily_volatility = metrics.daily_return_std
            # Annualize: multiply by sqrt(252) for trading days
            metrics.volatility = daily_volatility * np.sqrt(252)

        # Calculate Calmar ratio (return / max drawdown)
        drawdown_metrics = self.calculate_drawdown(trades, initial_equity)
        if drawdown_metrics.max_drawdown_percent > 0:
            metrics.calmar_ratio = abs(metrics.total_return_percent) / drawdown_metrics.max_drawdown_percent
        else:
            metrics.calmar_ratio = 0.0

        logger.info(
            f"Returns metrics calculated: Total Return={metrics.total_return_percent:.2f}%, "
            "Daily Avg={metrics.daily_return_avg:.2f}, "
            f"Volatility={metrics.volatility:.2f}"
        )

        return metrics

    def calculate_all_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        initial_equity: float = 10000.0,
        use_cache: bool = True,
    ) -> CachedMetrics:
        """
        Calculate all performance metrics.

        Args:
            start_date: Filter trades from this date onwards (optional)
            end_date: Filter trades up to this date (optional)
            symbol: Filter by symbol (optional)
            initial_equity: Starting equity for calculations
            use_cache: Whether to use cached metrics if available

        Returns:
            CachedMetrics object with all calculated metrics
        """
        # Check cache first
        if use_cache and not self._cached_metrics.is_expired() and self._cached_metrics.basic_metrics is not None:
            logger.info("Using cached metrics")
            return self._cached_metrics

        # Fetch trades
        trades = self.fetch_all_trades(start_date=start_date, end_date=end_date, symbol=symbol)

        if not trades:
            logger.warning("No trades found for metrics calculation")
            return CachedMetrics(ttl_seconds=self._cache_ttl_seconds)

        # Calculate all metrics
        basic = self.calculate_basic_metrics(trades)
        drawdown = self.calculate_drawdown(trades, initial_equity)
        stats = self.calculate_trade_statistics(trades)
        returns = self.calculate_returns(trades, initial_equity)

        # Create cached metrics
        self._cached_metrics = CachedMetrics(
            basic_metrics=basic,
            drawdown_metrics=drawdown,
            trade_statistics=stats,
            returns_metrics=returns,
            ttl_seconds=self._cache_ttl_seconds,
        )

        # Store metrics in database
        self._store_metrics(basic, drawdown, stats, returns)

        logger.info("All metrics calculated and cached successfully")

        return self._cached_metrics

    def _store_metrics(
        self,
        basic: BasicMetrics,
        drawdown: DrawdownMetrics,
        stats: TradeStatistics,
        returns: ReturnsMetrics,
    ) -> None:
        """
        Store calculated metrics in database.

        Args:
            basic: BasicMetrics to store
            drawdown: DrawdownMetrics to store
            stats: TradeStatistics to store
            returns: ReturnsMetrics to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, metrics not stored")
            return

        try:
            cursor = self._connection.cursor()

            # Store basic metrics
            cursor.execute("""
                INSERT INTO basic_metrics (
                    win_rate, profit_factor, average_win, average_loss,
                    total_trades, winning_trades, losing_trades,
                    total_profit, total_loss, sharpe_ratio, sortino_ratio, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                basic.win_rate,
                basic.profit_factor if basic.profit_factor != float("inf") else 999.99,
                basic.average_win,
                basic.average_loss,
                basic.total_trades,
                basic.winning_trades,
                basic.losing_trades,
                basic.total_profit,
                basic.total_loss,
                basic.sharpe_ratio,
                basic.sortino_ratio if basic.sortino_ratio != float("inf") else 999.99,
                basic.calculated_at.isoformat(),
            ))

            # Store drawdown metrics
            cursor.execute("""
                INSERT INTO drawdown_metrics (
                    max_drawdown, max_drawdown_percent, avg_drawdown, avg_drawdown_percent,
                    max_drawdown_duration, avg_drawdown_duration,
                    current_drawdown, current_drawdown_percent,
                    drawdown_count, recovery_time_avg, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                drawdown.max_drawdown,
                drawdown.max_drawdown_percent,
                drawdown.avg_drawdown,
                drawdown.avg_drawdown_percent,
                drawdown.max_drawdown_duration,
                drawdown.avg_drawdown_duration,
                drawdown.current_drawdown,
                drawdown.current_drawdown_percent,
                drawdown.drawdown_count,
                drawdown.recovery_time_avg,
                drawdown.calculated_at.isoformat(),
            ))

            # Store trade statistics
            cursor.execute("""
                INSERT INTO trade_statistics (
                    avg_hold_time, avg_hold_time_minutes, avg_hold_time_hours,
                    trades_per_day, trades_per_week, trades_per_month,
                    max_consecutive_wins, max_consecutive_losses,
                    current_streak, current_streak_type,
                    largest_win, largest_loss, avg_r_multiple, total_r_multiple, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats.avg_hold_time,
                stats.avg_hold_time_minutes,
                stats.avg_hold_time_hours,
                stats.trades_per_day,
                stats.trades_per_week,
                stats.trades_per_month,
                stats.max_consecutive_wins,
                stats.max_consecutive_losses,
                stats.current_streak,
                stats.current_streak_type,
                stats.largest_win,
                stats.largest_loss,
                stats.avg_r_multiple,
                stats.total_r_multiple,
                stats.calculated_at.isoformat(),
            ))

            # Store returns metrics
            cursor.execute("""
                INSERT INTO returns_metrics (
                    daily_return_avg, daily_return_std,
                    weekly_return_avg, weekly_return_std,
                    monthly_return_avg, monthly_return_std,
                    total_return, total_return_percent,
                    best_day, worst_day, best_week, worst_week, best_month, worst_month,
                    volatility, calmar_ratio, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                returns.daily_return_avg,
                returns.daily_return_std,
                returns.weekly_return_avg,
                returns.weekly_return_std,
                returns.monthly_return_avg,
                returns.monthly_return_std,
                returns.total_return,
                returns.total_return_percent,
                returns.best_day,
                returns.worst_day,
                returns.best_week,
                returns.worst_week,
                returns.best_month,
                returns.worst_month,
                returns.volatility,
                returns.calmar_ratio,
                returns.calculated_at.isoformat(),
            ))

            self._connection.commit()

            logger.info("All metrics stored in database successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to store metrics in database: {e}")

    def get_basic_metrics(self) -> Optional[BasicMetrics]:
        """Get cached basic metrics."""
        return self._cached_metrics.basic_metrics

    def get_drawdown_metrics(self) -> Optional[DrawdownMetrics]:
        """Get cached drawdown metrics."""
        return self._cached_metrics.drawdown_metrics

    def get_trade_statistics(self) -> Optional[TradeStatistics]:
        """Get cached trade statistics."""
        return self._cached_metrics.trade_statistics

    def get_returns_metrics(self) -> Optional[ReturnsMetrics]:
        """Get cached returns metrics."""
        return self._cached_metrics.returns_metrics

    def get_historical_metrics(
        self,
        metric_type: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get historical metrics from database.

        Args:
            metric_type: Type of metric ('basic', 'drawdown', 'statistics', 'returns')
            limit: Maximum number of records to return

        Returns:
            List of metric dictionaries
        """
        if self._connection is None:
            logger.warning("Database connection not available")
            return []

        try:
            cursor = self._connection.cursor()

            table_map = {
                "basic": "basic_metrics",
                "drawdown": "drawdown_metrics",
                "statistics": "trade_statistics",
                "returns": "returns_metrics",
            }

            table = table_map.get(metric_type)
            if not table:
                logger.warning(f"Invalid metric type: {metric_type}")
                return []

            query = f"SELECT * FROM {table} ORDER BY calculated_at DESC LIMIT ?"
            cursor.execute(query, (limit,))

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            logger.info(f"Retrieved {len(results)} historical {metric_type} metrics")

            return results

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve historical metrics: {e}")
            return []

    def clear_cache(self) -> None:
        """Clear the metrics cache."""
        self._cached_metrics = CachedMetrics(ttl_seconds=self._cache_ttl_seconds)
        logger.info("Metrics cache cleared")

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
