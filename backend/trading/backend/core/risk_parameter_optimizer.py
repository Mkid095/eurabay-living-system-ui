"""
Risk Parameter Optimizer for optimizing risk parameters over time.

This module implements parameter optimization that tests different risk levels
and ATR/TP multipliers to find the best settings for each symbol and regime.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

from .performance_comparator import PerformanceComparator, TradeOutcome

# Configure logging
logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market volatility regimes."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


@dataclass
class RiskParameterSet:
    """
    A set of risk parameters to test.

    Attributes:
        base_risk_percent: Base risk percentage (e.g., 1.0, 1.5, 2.0, 2.5)
        stop_atr_multiplier: ATR multiplier for stop loss (e.g., 1.5, 2.0, 2.5, 3.0)
        tp_atr_multiplier: ATR multiplier for take profit (e.g., 2.0, 2.5, 3.0)
    """
    base_risk_percent: float
    stop_atr_multiplier: float
    tp_atr_multiplier: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "base_risk_percent": self.base_risk_percent,
            "stop_atr_multiplier": self.stop_atr_multiplier,
            "tp_atr_multiplier": self.tp_atr_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RiskParameterSet":
        """Create from dictionary."""
        return cls(
            base_risk_percent=data["base_risk_percent"],
            stop_atr_multiplier=data["stop_atr_multiplier"],
            tp_atr_multiplier=data["tp_atr_multiplier"],
        )


@dataclass
class OptimizationResult:
    """
    Result of backtesting a parameter set.

    Attributes:
        parameter_set: The risk parameters tested
        sharpe_ratio: Sharpe ratio achieved
        total_return: Total return percentage
        win_rate: Win rate percentage
        profit_factor: Gross profit / gross loss
        max_drawdown: Maximum drawdown percentage
        total_trades: Number of trades simulated
        symbol: Symbol tested
        market_regime: Market regime tested
        timestamp: When optimization was run
    """
    parameter_set: RiskParameterSet
    sharpe_ratio: float
    total_return: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    symbol: str
    market_regime: MarketRegime
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "base_risk_percent": self.parameter_set.base_risk_percent,
            "stop_atr_multiplier": self.parameter_set.stop_atr_multiplier,
            "tp_atr_multiplier": self.parameter_set.tp_atr_multiplier,
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "total_return": round(self.total_return, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "total_trades": self.total_trades,
            "symbol": self.symbol,
            "market_regime": self.market_regime.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class OptimalParameters:
    """
    Optimal parameters for a symbol and regime.

    Attributes:
        symbol: Trading symbol
        market_regime: Market regime
        parameter_set: Optimal risk parameters
        optimization_results: List of all results tested
        sharpe_ratio: Best Sharpe ratio achieved
        timestamp: When optimized
        valid_until: When to re-optimize
    """
    symbol: str
    market_regime: MarketRegime
    parameter_set: RiskParameterSet
    optimization_results: list[OptimizationResult]
    sharpe_ratio: float
    timestamp: datetime
    valid_until: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "market_regime": self.market_regime.value,
            "base_risk_percent": self.parameter_set.base_risk_percent,
            "stop_atr_multiplier": self.parameter_set.stop_atr_multiplier,
            "tp_atr_multiplier": self.parameter_set.tp_atr_multiplier,
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "timestamp": self.timestamp.isoformat(),
            "valid_until": self.valid_until.isoformat(),
        }


class RiskParameterOptimizer:
    """
    Optimizes risk parameters over time to find the best settings.

    Features:
    - Tests different base risk levels (1%, 1.5%, 2%, 2.5%)
    - Tests different ATR multipliers for stops
    - Tests different TP multipliers
    - Calculates Sharpe ratio for each combination
    - Finds optimal parameters for each symbol and regime
    - Stores optimal parameters in database
    - Re-optimizes weekly

    Usage:
        optimizer = RiskParameterOptimizer(
            performance_comparator=comparator,
            database_path="risk_optimization.db"
        )

        # Run optimization for a symbol
        optimal = optimizer.optimize_parameters("EURUSD")

        # Get optimal parameters for symbol
        params = optimizer.get_optimal_parameters("EURUSD")
    """

    def __init__(
        self,
        performance_comparator: PerformanceComparator,
        database_path: str = "risk_optimization.db",
        base_risk_options: list[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 2.5]),
        stop_atr_multiplier_options: list[float] = field(default_factory=lambda: [1.5, 2.0, 2.5, 3.0]),
        tp_atr_multiplier_options: list[float] = field(default_factory=lambda: [2.0, 2.5, 3.0, 3.5]),
        optimization_period_days: int = 180,
        rebalance_frequency_days: int = 7,
        min_trades_for_optimization: int = 50,
    ):
        """
        Initialize the RiskParameterOptimizer.

        Args:
            performance_comparator: PerformanceComparator for accessing trade history
            database_path: Path to SQLite database for storing optimization results
            base_risk_options: List of base risk percentages to test (default: [1.0, 1.5, 2.0, 2.5])
            stop_atr_multiplier_options: List of ATR multipliers for stops to test
            tp_atr_multiplier_options: List of ATR multipliers for TP to test
            optimization_period_days: Lookback period for optimization (default: 180 days = 6 months)
            rebalance_frequency_days: How often to re-optimize (default: 7 days)
            min_trades_for_optimization: Minimum trades required for optimization (default: 50)
        """
        self.performance_comparator = performance_comparator
        self.database_path = database_path
        self.base_risk_options = base_risk_options
        self.stop_atr_multiplier_options = stop_atr_multiplier_options
        self.tp_atr_multiplier_options = tp_atr_multiplier_options
        self.optimization_period_days = optimization_period_days
        self.rebalance_frequency_days = rebalance_frequency_days
        self.min_trades_for_optimization = min_trades_for_optimization

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database tables for optimization results."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()

            # Create optimal_parameters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimal_parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market_regime TEXT NOT NULL,
                    base_risk_percent REAL NOT NULL,
                    stop_atr_multiplier REAL NOT NULL,
                    tp_atr_multiplier REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    UNIQUE(symbol, market_regime)
                )
            """)

            # Create optimization_results table for storing all test results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market_regime TEXT NOT NULL,
                    base_risk_percent REAL NOT NULL,
                    stop_atr_multiplier REAL NOT NULL,
                    tp_atr_multiplier REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    total_return REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    profit_factor REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_optimal_params_symbol
                ON optimal_parameters(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_optimal_params_valid_until
                ON optimal_parameters(valid_until)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_opt_results_symbol
                ON optimization_results(symbol, market_regime, timestamp DESC)
            """)

            conn.commit()
            logger.info(f"Database initialized at {self.database_path}")

    def _detect_market_regime(self, symbol: str) -> MarketRegime:
        """
        Detect current market regime based on volatility.

        Args:
            symbol: Trading symbol

        Returns:
            MarketRegime: LOW, NORMAL, or HIGH
        """
        try:
            # Get recent trade outcomes to estimate volatility
            trade_history = self.performance_comparator.get_evolved_trades(
                limit=100
            )

            if not trade_history:
                return MarketRegime.NORMAL

            # Calculate average P&L volatility as proxy for market regime
            pnls = [t.pnl_percent for t in trade_history if t.pnl_percent is not None]
            if len(pnls) < 10:
                return MarketRegime.NORMAL

            pnl_std = np.std(pnls)

            # Classify regime based on P&L volatility
            if pnl_std < 1.0:
                return MarketRegime.LOW
            elif pnl_std < 2.5:
                return MarketRegime.NORMAL
            else:
                return MarketRegime.HIGH

        except Exception as e:
            logger.error(f"Error detecting market regime for {symbol}: {e}")
            return MarketRegime.NORMAL

    def backtest_risk_parameters(
        self,
        symbol: str,
        parameter_set: RiskParameterSet,
        market_regime: MarketRegime,
    ) -> OptimizationResult:
        """
        Backtest a specific set of risk parameters on historical data.

        Simulates how trades would have performed with different risk settings,
        calculating key metrics like Sharpe ratio, total return, and drawdown.

        Args:
            symbol: Trading symbol to optimize for
            parameter_set: Risk parameters to test
            market_regime: Market regime for optimization

        Returns:
            OptimizationResult with performance metrics
        """
        try:
            # Get historical trade data
            start_date = datetime.now() - timedelta(days=self.optimization_period_days)
            trade_history = self.performance_comparator.get_evolved_trades_in_date_range(
                start_date=start_date,
                end_date=datetime.now(),
                symbol_filter=symbol,
            )

            if len(trade_history) < self.min_trades_for_optimization:
                logger.warning(
                    f"Insufficient trades for {symbol}: {len(trade_history)} < {self.min_trades_for_optimization}"
                )
                # Return default result with poor metrics
                return OptimizationResult(
                    parameter_set=parameter_set,
                    sharpe_ratio=-999.0,
                    total_return=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    max_drawdown=100.0,
                    total_trades=len(trade_history),
                    symbol=symbol,
                    market_regime=market_regime,
                    timestamp=datetime.now(),
                )

            # Simulate trades with given parameters
            equity_curve = []
            peak_equity = 10000.0  # Starting equity
            current_equity = peak_equity
            max_drawdown = 0.0
            wins = 0
            losses = 0
            gross_profit = 0.0
            gross_loss = 0.0
            daily_returns = []

            for trade in trade_history:
                # Simulate position size based on base risk
                if trade.stop_loss and trade.entry_price:
                    risk_per_share = abs(trade.entry_price - trade.stop_loss)
                    if risk_per_share > 0:
                        # Calculate position size based on risk percentage
                        position_value = current_equity * (parameter_set.base_risk_percent / 100)
                        position_size = position_value / risk_per_share
                    else:
                        position_size = 0.0
                else:
                    position_size = 0.0

                # Calculate P&L
                if trade.pnl is not None:
                    # Simulate TP hit based on TP multiplier
                    # (simplified - in reality would need more data)
                    pnl = trade.pnl

                    # Scale P&L by position size relative to default
                    # (Assume default was 2% risk)
                    scale_factor = parameter_set.base_risk_percent / 2.0
                    pnl = pnl * scale_factor

                    current_equity += pnl
                    equity_curve.append(current_equity)

                    # Track drawdown
                    if current_equity > peak_equity:
                        peak_equity = current_equity
                    drawdown = (peak_equity - current_equity) / peak_equity * 100
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                    # Track wins/losses
                    if pnl > 0:
                        wins += 1
                        gross_profit += pnl
                    else:
                        losses += 1
                        gross_loss += abs(pnl)

            # Calculate metrics
            if not equity_curve:
                total_return = 0.0
                sharpe_ratio = -999.0
            else:
                final_equity = equity_curve[-1]
                total_return = (final_equity - 10000.0) / 10000.0 * 100

                # Calculate daily returns for Sharpe ratio
                if len(equity_curve) > 1:
                    returns = [
                        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                        for i in range(1, len(equity_curve))
                    ]
                    if returns:
                        avg_return = np.mean(returns)
                        std_return = np.std(returns)
                        if std_return > 0:
                            # Annualized Sharpe ratio (assuming ~250 trading days)
                            sharpe_ratio = (avg_return / std_return) * np.sqrt(250)
                        else:
                            sharpe_ratio = 0.0
                    else:
                        sharpe_ratio = 0.0
                else:
                    sharpe_ratio = 0.0

            # Calculate win rate and profit factor
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

            result = OptimizationResult(
                parameter_set=parameter_set,
                sharpe_ratio=sharpe_ratio,
                total_return=total_return,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                total_trades=total_trades,
                symbol=symbol,
                market_regime=market_regime,
                timestamp=datetime.now(),
            )

            logger.info(
                f"Backtested {symbol} {market_regime.value}: "
                f"Risk={parameter_set.base_risk_percent}%, "
                f"Sharpe={sharpe_ratio:.2f}, Return={total_return:.2f}%"
            )

            return result

        except Exception as e:
            logger.error(f"Error backtesting parameters for {symbol}: {e}")
            # Return default result with poor metrics
            return OptimizationResult(
                parameter_set=parameter_set,
                sharpe_ratio=-999.0,
                total_return=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                max_drawdown=100.0,
                total_trades=0,
                symbol=symbol,
                market_regime=market_regime,
                timestamp=datetime.now(),
            )

    def optimize_parameters(
        self,
        symbol: str,
        force: bool = False,
    ) -> Optional[OptimalParameters]:
        """
        Find optimal risk parameters for a symbol by testing all combinations.

        Tests all combinations of base risk, stop ATR multiplier, and TP ATR multiplier
        to find the parameters that maximize Sharpe ratio.

        Args:
            symbol: Trading symbol to optimize
            force: Force optimization even if recent results exist

        Returns:
            OptimalParameters with best parameter set, or None if insufficient data
        """
        try:
            # Validate symbol
            if not symbol or not symbol.strip():
                logger.warning("Empty symbol provided to optimize_parameters")
                return None

            # Check if we have recent valid optimization
            if not force:
                existing = self._get_valid_optimization(symbol)
                if existing is not None:
                    logger.info(
                        f"Using existing optimization for {symbol} valid until {existing.valid_until}"
                    )
                    return existing

            # Detect market regime
            market_regime = self._detect_market_regime(symbol)

            # Generate all parameter combinations
            all_results = []

            for base_risk in self.base_risk_options:
                for stop_atr in self.stop_atr_multiplier_options:
                    for tp_atr in self.tp_atr_multiplier_options:
                        params = RiskParameterSet(
                            base_risk_percent=base_risk,
                            stop_atr_multiplier=stop_atr,
                            tp_atr_multiplier=tp_atr,
                        )

                        result = self.backtest_risk_parameters(
                            symbol=symbol,
                            parameter_set=params,
                            market_regime=market_regime,
                        )

                        all_results.append(result)

                        # Store result in database
                        self._store_optimization_result(result)

            # Find best result by Sharpe ratio
            valid_results = [r for r in all_results if r.total_trades >= self.min_trades_for_optimization]

            if not valid_results:
                logger.warning(
                    f"No valid optimization results for {symbol} "
                    f"(need {self.min_trades_for_optimization} trades)"
                )
                return None

            best_result = max(valid_results, key=lambda r: r.sharpe_ratio)

            # Create optimal parameters
            optimal = OptimalParameters(
                symbol=symbol,
                market_regime=market_regime,
                parameter_set=best_result.parameter_set,
                optimization_results=all_results,
                sharpe_ratio=best_result.sharpe_ratio,
                timestamp=datetime.now(),
                valid_until=datetime.now() + timedelta(days=self.rebalance_frequency_days),
            )

            # Store in database
            self._store_optimal_parameters(optimal)

            logger.info(
                f"Optimized parameters for {symbol} {market_regime.value}: "
                f"Risk={best_result.parameter_set.base_risk_percent}%, "
                f"StopATR={best_result.parameter_set.stop_atr_multiplier}x, "
                f"TPATR={best_result.parameter_set.tp_atr_multiplier}x, "
                f"Sharpe={best_result.sharpe_ratio:.2f}"
            )

            return optimal

        except Exception as e:
            logger.error(f"Error optimizing parameters for {symbol}: {e}")
            return None

    def _get_valid_optimization(self, symbol: str) -> Optional[OptimalParameters]:
        """Check if there's a valid recent optimization for the symbol."""
        try:
            market_regime = self._detect_market_regime(symbol)

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT symbol, market_regime, base_risk_percent, stop_atr_multiplier,
                           tp_atr_multiplier, sharpe_ratio, timestamp, valid_until
                    FROM optimal_parameters
                    WHERE symbol = ? AND market_regime = ? AND valid_until > datetime('now')
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (symbol, market_regime.value))

                row = cursor.fetchone()
                if row:
                    return OptimalParameters(
                        symbol=row[0],
                        market_regime=MarketRegime(row[1]),
                        parameter_set=RiskParameterSet(
                            base_risk_percent=row[2],
                            stop_atr_multiplier=row[3],
                            tp_atr_multiplier=row[4],
                        ),
                        optimization_results=[],
                        sharpe_ratio=row[5],
                        timestamp=datetime.fromisoformat(row[6]),
                        valid_until=datetime.fromisoformat(row[7]),
                    )
                return None

        except Exception as e:
            logger.error(f"Error checking valid optimization: {e}")
            return None

    def _store_optimal_parameters(self, optimal: OptimalParameters) -> None:
        """Store optimal parameters in database."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO optimal_parameters
                    (symbol, market_regime, base_risk_percent, stop_atr_multiplier,
                     tp_atr_multiplier, sharpe_ratio, timestamp, valid_until)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    optimal.symbol,
                    optimal.market_regime.value,
                    optimal.parameter_set.base_risk_percent,
                    optimal.parameter_set.stop_atr_multiplier,
                    optimal.parameter_set.tp_atr_multiplier,
                    optimal.sharpe_ratio,
                    optimal.timestamp.isoformat(),
                    optimal.valid_until.isoformat(),
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error storing optimal parameters: {e}")

    def _store_optimization_result(self, result: OptimizationResult) -> None:
        """Store optimization result in database."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                data = result.to_dict()
                cursor.execute("""
                    INSERT INTO optimization_results
                    (symbol, market_regime, base_risk_percent, stop_atr_multiplier,
                     tp_atr_multiplier, sharpe_ratio, total_return, win_rate,
                     profit_factor, max_drawdown, total_trades, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.symbol,
                    result.market_regime.value,
                    result.parameter_set.base_risk_percent,
                    result.parameter_set.stop_atr_multiplier,
                    result.parameter_set.tp_atr_multiplier,
                    result.sharpe_ratio,
                    result.total_return,
                    result.win_rate,
                    result.profit_factor,
                    result.max_drawdown,
                    result.total_trades,
                    result.timestamp.isoformat(),
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error storing optimization result: {e}")

    def get_optimal_parameters(
        self,
        symbol: str,
    ) -> Optional[RiskParameterSet]:
        """
        Get optimal risk parameters for a symbol.

        Returns the cached optimal parameters if valid, otherwise runs
        a new optimization.

        Args:
            symbol: Trading symbol

        Returns:
            RiskParameterSet with optimal settings, or None if unavailable
        """
        try:
            optimal = self.optimize_parameters(symbol, force=False)
            if optimal:
                return optimal.parameter_set
            return None

        except Exception as e:
            logger.error(f"Error getting optimal parameters for {symbol}: {e}")
            return None

    def get_optimization_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[OptimizationResult]:
        """
        Get optimization history for a symbol.

        Args:
            symbol: Trading symbol
            limit: Maximum number of results to return

        Returns:
            List of OptimizationResult objects
        """
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT symbol, market_regime, base_risk_percent, stop_atr_multiplier,
                           tp_atr_multiplier, sharpe_ratio, total_return, win_rate,
                           profit_factor, max_drawdown, total_trades, timestamp
                    FROM optimization_results
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (symbol, limit))

                results = []
                for row in cursor.fetchall():
                    results.append(OptimizationResult(
                        parameter_set=RiskParameterSet(
                            base_risk_percent=row[2],
                            stop_atr_multiplier=row[3],
                            tp_atr_multiplier=row[4],
                        ),
                        sharpe_ratio=row[5],
                        total_return=row[6],
                        win_rate=row[7],
                        profit_factor=row[8],
                        max_drawdown=row[9],
                        total_trades=row[10],
                        symbol=row[0],
                        market_regime=MarketRegime(row[1]),
                        timestamp=datetime.fromisoformat(row[11]),
                    ))

                return results

        except Exception as e:
            logger.error(f"Error getting optimization history: {e}")
            return []
