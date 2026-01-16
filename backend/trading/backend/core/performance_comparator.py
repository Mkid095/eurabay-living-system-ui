"""
Performance Comparator for Active vs Passive Trade Management.

This module implements comprehensive performance comparison between actively
managed trades and set-and-forget (passive) trades to prove the value of
active management.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .trade_state import TradePosition, TradeState
from .trade_lifecycle_logger import TradeLifecycleLogger, ManagementAction


# Configure logging
logger = logging.getLogger(__name__)


class ManagementActionType(Enum):
    """
    Types of management actions to track for effectiveness analysis.

    Actions:
        TRAILING_STOP: Trailing stop updates
        BREAKEVEN: Breakeven triggers
        PARTIAL_PROFIT: Partial profit taking
        HOLDING_TIME_LIMIT: Holding time limit closures
    """

    TRAILING_STOP = "trailing_stop"
    BREAKEVEN = "breakeven"
    PARTIAL_PROFIT = "partial_profit"
    HOLDING_TIME_LIMIT = "holding_time_limit"


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for a set of trades.

    Attributes:
        total_trades: Total number of trades analyzed
        winning_trades: Number of profitable trades
        losing_trades: Number of unprofitable trades
        win_rate: Percentage of winning trades (0-100)
        total_profit: Sum of all profits
        total_loss: Sum of all losses (absolute value)
        profit_factor: Ratio of total profit to total loss
        average_win: Average profit per winning trade
        average_loss: Average loss per losing trade
        max_drawdown: Maximum drawdown observed
        average_holding_time: Average time positions were held
        total_r: Total R-multiple gained
        average_r: Average R-multiple per trade
        best_trade: Best single trade profit
        worst_trade: Worst single trade loss
    """

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_drawdown: float = 0.0
    average_holding_time: timedelta = field(default_factory=lambda: timedelta(0))
    total_r: float = 0.0
    average_r: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage/serialization."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            "total_profit": round(self.total_profit, 2),
            "total_loss": round(self.total_loss, 2),
            "profit_factor": round(self.profit_factor, 2) if self.profit_factor > 0 else 0,
            "average_win": round(self.average_win, 2),
            "average_loss": round(self.average_loss, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "average_holding_time_seconds": int(self.average_holding_time.total_seconds()),
            "total_r": round(self.total_r, 2),
            "average_r": round(self.average_r, 2),
            "best_trade": round(self.best_trade, 2),
            "worst_trade": round(self.worst_trade, 2),
        }


@dataclass
class ActionEffectiveness:
    """
    Effectiveness metrics for a specific management action.

    Attributes:
        action_type: Type of management action
        times_triggered: How many times this action was triggered
        profit_saved: Total profit saved by this action
        loss_prevented: Total loss prevented by this action
        average_benefit: Average benefit per trigger
        success_rate: Percentage of times action was beneficial
    """

    action_type: ManagementActionType
    times_triggered: int = 0
    profit_saved: float = 0.0
    loss_prevented: float = 0.0
    average_benefit: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "action_type": self.action_type.value,
            "times_triggered": self.times_triggered,
            "profit_saved": round(self.profit_saved, 2),
            "loss_prevented": round(self.loss_prevented, 2),
            "average_benefit": round(self.average_benefit, 2),
            "success_rate": round(self.success_rate, 2),
        }


@dataclass
class ComparisonResult:
    """
    Result of comparing active vs passive management.

    Attributes:
        active_metrics: Metrics for actively managed trades
        passive_metrics: Metrics for set-and-forget trades
        win_rate_improvement: Percentage improvement in win rate
        profit_factor_improvement: Absolute improvement in profit factor
        total_profit_improvement: Additional profit from active management
        action_effectiveness: List of action effectiveness metrics
        recommendation: Summary recommendation
    """

    active_metrics: PerformanceMetrics
    passive_metrics: PerformanceMetrics
    win_rate_improvement: float
    profit_factor_improvement: float
    total_profit_improvement: float
    action_effectiveness: list[ActionEffectiveness]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "active_metrics": self.active_metrics.to_dict(),
            "passive_metrics": self.passive_metrics.to_dict(),
            "win_rate_improvement": round(self.win_rate_improvement, 2),
            "profit_factor_improvement": round(self.profit_factor_improvement, 2),
            "total_profit_improvement": round(self.total_profit_improvement, 2),
            "action_effectiveness": [ae.to_dict() for ae in self.action_effectiveness],
            "recommendation": self.recommendation,
        }


@dataclass
class TradeOutcome:
    """
    Outcome of a single trade for comparison.

    Attributes:
        ticket: Position ticket number
        symbol: Trading symbol
        direction: "BUY" or "SELL"
        entry_price: Entry price
        exit_price: Exit price (or current price if still open)
        entry_time: When position was opened
        exit_time: When position was closed (None if open)
        initial_stop_loss: Initial stop loss price
        initial_take_profit: Initial take profit price
        final_profit: Actual profit/loss
        passive_profit: What-if profit if no active management
        holding_time: How long position was held
        management_actions: List of management actions taken
        peak_profit: Maximum profit reached during trade
        max_adverse_excursion: Maximum loss reached during trade
        volume: Position size in lots
    """

    ticket: int
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: Optional[datetime]
    initial_stop_loss: Optional[float]
    initial_take_profit: Optional[float]
    final_profit: float
    passive_profit: float
    holding_time: timedelta
    management_actions: list[str]
    peak_profit: float = 0.0
    max_adverse_excursion: float = 0.0
    volume: float = 1.0


class PerformanceComparator:
    """
    Compares performance of actively managed trades vs set-and-forget trades.

    Features:
    - Tracks actively managed trades performance
    - Calculates what-if scenarios for set-and-forget trades
    - Compares metrics: win rate, profit factor, average win/loss, max drawdown
    - Calculates improvement percentages
    - Tracks individual action effectiveness
    - Stores comparison data in database
    - Generates performance comparison reports
    - Tests on historical data

    Usage:
        comparator = PerformanceComparator(database_path="performance.db")

        # Record a trade outcome
        comparator.record_trade_outcome(
            position=position,
            final_profit=150.0,
            management_actions=[...]
        )

        # Generate comparison report
        report = comparator.generate_comparison_report()

        # Get action effectiveness
        trailing_stop_stats = comparator.get_action_effectiveness(
            ManagementActionType.TRAILING_STOP
        )
    """

    def __init__(
        self,
        database_path: str = "performance_comparison.db",
        lifecycle_logger: Optional[TradeLifecycleLogger] = None,
    ):
        """
        Initialize the PerformanceComparator.

        Args:
            database_path: Path to SQLite database for storing comparison data
            lifecycle_logger: Optional TradeLifecycleLogger for accessing lifecycle data
        """
        self._database_path = database_path
        self._lifecycle_logger = lifecycle_logger
        self._connection: Optional[sqlite3.Connection] = None
        self._trade_outcomes: list[TradeOutcome] = []
        self._action_effectiveness: dict[ManagementActionType, ActionEffectiveness] = {}

        # Initialize action effectiveness trackers
        for action_type in ManagementActionType:
            self._action_effectiveness[action_type] = ActionEffectiveness(
                action_type=action_type
            )

        # Initialize database
        self._initialize_database()

        logger.info(
            f"PerformanceComparator initialized with database: {database_path}"
        )

    def _initialize_database(self) -> None:
        """
        Initialize the SQLite database with required tables.

        Creates tables for:
        - trade_outcomes: Trade outcome data
        - performance_comparisons: Comparison snapshots
        - action_effectiveness: Action effectiveness data
        """
        try:
            self._connection = sqlite3.connect(self._database_path)
            cursor = self._connection.cursor()

            # Create trade_outcomes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER NOT NULL UNIQUE,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    initial_stop_loss REAL,
                    initial_take_profit REAL,
                    final_profit REAL NOT NULL,
                    passive_profit REAL NOT NULL,
                    holding_time_seconds INTEGER NOT NULL,
                    management_actions TEXT,
                    peak_profit REAL DEFAULT 0,
                    max_adverse_excursion REAL DEFAULT 0,
                    volume REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create performance_comparisons table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comparison_date TEXT NOT NULL,
                    active_win_rate REAL NOT NULL,
                    passive_win_rate REAL NOT NULL,
                    active_profit_factor REAL NOT NULL,
                    passive_profit_factor REAL NOT NULL,
                    active_total_profit REAL NOT NULL,
                    passive_total_profit REAL NOT NULL,
                    win_rate_improvement REAL NOT NULL,
                    profit_factor_improvement REAL NOT NULL,
                    total_profit_improvement REAL NOT NULL,
                    active_total_trades INTEGER NOT NULL,
                    passive_total_trades INTEGER NOT NULL,
                    summary TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create action_effectiveness table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_effectiveness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    times_triggered INTEGER NOT NULL,
                    profit_saved REAL NOT NULL,
                    loss_prevented REAL NOT NULL,
                    average_benefit REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    comparison_date TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(action_type, comparison_date)
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_outcomes_ticket
                ON trade_outcomes(ticket)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_outcomes_date
                ON trade_outcomes(entry_time)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_comparisons_date
                ON performance_comparisons(comparison_date)
            """)

            self._connection.commit()

            logger.info("Performance comparison database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def record_trade_outcome(
        self,
        position: TradePosition,
        exit_price: float,
        exit_time: Optional[datetime],
        final_profit: float,
        peak_profit: float = 0.0,
        max_adverse_excursion: float = 0.0,
        management_actions: Optional[list[str]] = None,
    ) -> TradeOutcome:
        """
        Record the outcome of a trade for comparison.

        Args:
            position: TradePosition that was managed
            exit_price: Price at exit (or current price if open)
            exit_time: Time of exit (None if still open)
            final_profit: Final profit/loss of the trade
            peak_profit: Maximum profit reached during trade
            max_adverse_excursion: Maximum loss reached during trade
            management_actions: List of management actions taken

        Returns:
            TradeOutcome object with recorded data
        """
        # Calculate holding time
        if exit_time:
            holding_time = exit_time - position.entry_time
        else:
            holding_time = datetime.utcnow() - position.entry_time

        # Calculate passive profit (what-if scenario)
        passive_profit = self._calculate_passive_profit(
            position, exit_price, peak_profit, max_adverse_excursion
        )

        # Create outcome
        outcome = TradeOutcome(
            ticket=position.ticket,
            symbol=position.symbol,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=exit_time,
            initial_stop_loss=position.stop_loss,
            initial_take_profit=position.take_profit,
            final_profit=final_profit,
            passive_profit=passive_profit,
            holding_time=holding_time,
            management_actions=management_actions or [],
            peak_profit=peak_profit,
            max_adverse_excursion=max_adverse_excursion,
            volume=position.volume,
        )

        # Store in memory
        self._trade_outcomes.append(outcome)

        # Store in database
        self._store_trade_outcome(outcome)

        # Update action effectiveness
        self._update_action_effectiveness(outcome)

        logger.info(
            f"Recorded trade outcome for position {position.ticket}: "
            f"Active={final_profit:.2f}, Passive={passive_profit:.2f}, "
            f"Improvement={final_profit - passive_profit:.2f}"
        )

        return outcome

    def _calculate_passive_profit(
        self,
        position: TradePosition,
        exit_price: float,
        peak_profit: float,
        max_adverse_excursion: float,
    ) -> float:
        """
        Calculate what-if profit if trade was set-and-forget (no active management).

        In a passive scenario:
        - No trailing stops (SL stays at initial position)
        - No breakeven moves
        - No partial profit taking
        - No holding time limits
        - Position only exits at SL, TP, or manual close

        Args:
            position: The TradePosition
            exit_price: Actual exit price
            peak_profit: Maximum profit reached (in currency value)
            max_adverse_excursion: Maximum loss reached (in currency value)

        Returns:
            Calculated passive profit/loss (in currency value)
        """
        # If no initial SL or TP, passive profit is based on exit price
        # (no management means position exits where it currently is)
        if position.stop_loss is None and position.take_profit is None:
            lot_multiplier = position.volume * 100000
            if position.direction == "BUY":
                points_diff = exit_price - position.entry_price
            else:  # SELL
                points_diff = position.entry_price - exit_price
            return points_diff * lot_multiplier

        # Calculate the profit/loss if SL never moved
        # In passive scenario, position only exits at initial SL, initial TP, or manual close

        # Calculate initial SL and TP distances in points
        initial_risk_points = 0.0
        if position.stop_loss is not None:
            if position.direction == "BUY":
                initial_risk_points = position.entry_price - position.stop_loss
            else:
                initial_risk_points = position.stop_loss - position.entry_price

        initial_reward_points = 0.0
        if position.take_profit is not None:
            if position.direction == "BUY":
                initial_reward_points = position.take_profit - position.entry_price
            else:
                initial_reward_points = position.entry_price - position.take_profit

        # Convert peak_profit and max_adverse_excursion to points for comparison
        # Assuming standard lot size (100,000 units)
        lot_multiplier = position.volume * 100000

        peak_profit_points = peak_profit / lot_multiplier if lot_multiplier > 0 else 0
        max_adverse_points = abs(max_adverse_excursion) / lot_multiplier if lot_multiplier > 0 else 0

        # Determine which level would have been hit first in passive scenario
        # Priority: check if SL was hit, then check if TP was hit

        # If max adverse excursion reached or exceeded SL, SL would have been hit
        if initial_risk_points > 0 and max_adverse_points >= initial_risk_points:
            # SL would have been hit - result is loss equal to initial risk
            passive_profit = -initial_risk_points * lot_multiplier

        # If peak profit reached or exceeded TP, TP would have been hit
        elif initial_reward_points > 0 and peak_profit_points >= initial_reward_points:
            # TP would have been hit - result is profit equal to initial reward
            passive_profit = initial_reward_points * lot_multiplier

        else:
            # Neither SL nor TP was hit - use current exit price
            if position.direction == "BUY":
                points_diff = exit_price - position.entry_price
            else:  # SELL
                points_diff = position.entry_price - exit_price

            passive_profit = points_diff * lot_multiplier

        return passive_profit

    def _store_trade_outcome(self, outcome: TradeOutcome) -> None:
        """
        Store a trade outcome in the database.

        Args:
            outcome: TradeOutcome to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, outcome not stored")
            return

        try:
            cursor = self._connection.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO trade_outcomes (
                    ticket, symbol, direction, entry_price, exit_price,
                    entry_time, exit_time, initial_stop_loss, initial_take_profit,
                    final_profit, passive_profit, holding_time_seconds,
                    management_actions, peak_profit, max_adverse_excursion, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outcome.ticket,
                outcome.symbol,
                outcome.direction,
                outcome.entry_price,
                outcome.exit_price,
                outcome.entry_time.isoformat(),
                outcome.exit_time.isoformat() if outcome.exit_time else None,
                outcome.initial_stop_loss,
                outcome.initial_take_profit,
                outcome.final_profit,
                outcome.passive_profit,
                int(outcome.holding_time.total_seconds()),
                str(outcome.management_actions),
                outcome.peak_profit,
                outcome.max_adverse_excursion,
                outcome.volume,
            ))

            self._connection.commit()

            logger.debug(f"Trade outcome stored in database for position {outcome.ticket}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store trade outcome in database: {e}")

    def _update_action_effectiveness(self, outcome: TradeOutcome) -> None:
        """
        Update action effectiveness metrics based on trade outcome.

        Args:
            outcome: TradeOutcome to analyze
        """
        # Determine which actions were taken
        for action_str in outcome.management_actions:
            # Parse action type from string
            if "trailing_stop" in action_str:
                action_type = ManagementActionType.TRAILING_STOP
            elif "breakeven" in action_str:
                action_type = ManagementActionType.BREAKEVEN
            elif "partial_profit" in action_str or "partial_close" in action_str:
                action_type = ManagementActionType.PARTIAL_PROFIT
            elif "holding_time" in action_str:
                action_type = ManagementActionType.HOLDING_TIME_LIMIT
            else:
                continue

            effectiveness = self._action_effectiveness[action_type]
            effectiveness.times_triggered += 1

            # Calculate benefit
            benefit = outcome.final_profit - outcome.passive_profit

            if benefit > 0:
                effectiveness.profit_saved += benefit
            else:
                effectiveness.loss_prevented += abs(benefit)

        # Recalculate average and success rate
        for action_type, effectiveness in self._action_effectiveness.items():
            if effectiveness.times_triggered > 0:
                total_benefit = effectiveness.profit_saved + effectiveness.loss_prevented
                effectiveness.average_benefit = (
                    total_benefit / effectiveness.times_triggered
                )

                # Success rate = times benefit was positive / total times triggered
                # This is a simplified calculation
                effectiveness.success_rate = 50.0  # Placeholder

    def calculate_performance_metrics(
        self, outcomes: list[TradeOutcome], use_passive: bool = False
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics for a set of trade outcomes.

        Args:
            outcomes: List of TradeOutcome objects
            use_passive: If True, use passive_profit; otherwise use final_profit

        Returns:
            PerformanceMetrics object with calculated metrics
        """
        if not outcomes:
            return PerformanceMetrics()

        metrics = PerformanceMetrics()
        metrics.total_trades = len(outcomes)

        profits = []
        losses = []
        holding_times = []
        r_multiples = []

        for outcome in outcomes:
            profit = outcome.passive_profit if use_passive else outcome.final_profit
            holding_times.append(outcome.holding_time)

            if profit > 0:
                metrics.winning_trades += 1
                metrics.total_profit += profit
                profits.append(profit)
            elif profit < 0:
                metrics.losing_trades += 1
                metrics.total_loss += abs(profit)
                losses.append(profit)

            # Calculate R-multiple if initial risk known
            if outcome.initial_stop_loss is not None:
                if outcome.direction == "BUY":
                    initial_risk = outcome.entry_price - outcome.initial_stop_loss
                else:
                    initial_risk = outcome.initial_stop_loss - outcome.entry_price

                if initial_risk > 0:
                    r_multiple = profit / (initial_risk * outcome.volume * 100000)
                    r_multiples.append(r_multiple)

        # Calculate win rate
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100

        # Calculate average win/loss
        if profits:
            metrics.average_win = sum(profits) / len(profits)
            metrics.best_trade = max(profits)

        if losses:
            metrics.average_loss = sum(losses) / len(losses)
            metrics.worst_trade = min(losses)

        # Calculate profit factor
        if metrics.total_loss > 0:
            metrics.profit_factor = metrics.total_profit / metrics.total_loss
        elif metrics.total_profit > 0:
            metrics.profit_factor = float("inf")
        else:
            metrics.profit_factor = 0.0

        # Calculate average holding time
        if holding_times:
            total_time = sum(holding_times, timedelta())
            metrics.average_holding_time = total_time / len(holding_times)

        # Calculate R-multiples
        if r_multiples:
            metrics.total_r = sum(r_multiples)
            metrics.average_r = metrics.total_r / len(r_multiples)

        # Calculate max drawdown (simplified - uses worst trade)
        if losses:
            metrics.max_drawdown = abs(min(losses))

        return metrics

    def compare_performance(self) -> ComparisonResult:
        """
        Compare active vs passive performance.

        Returns:
            ComparisonResult with detailed comparison
        """
        if not self._trade_outcomes:
            logger.warning("No trade outcomes to compare")
            return ComparisonResult(
                active_metrics=PerformanceMetrics(),
                passive_metrics=PerformanceMetrics(),
                win_rate_improvement=0.0,
                profit_factor_improvement=0.0,
                total_profit_improvement=0.0,
                action_effectiveness=list(self._action_effectiveness.values()),
                recommendation="No trade data available for comparison",
            )

        # Calculate active metrics
        active_metrics = self.calculate_performance_metrics(
            self._trade_outcomes, use_passive=False
        )

        # Calculate passive metrics
        passive_metrics = self.calculate_performance_metrics(
            self._trade_outcomes, use_passive=True
        )

        # Calculate improvements
        win_rate_improvement = active_metrics.win_rate - passive_metrics.win_rate
        profit_factor_improvement = (
            active_metrics.profit_factor - passive_metrics.profit_factor
            if passive_metrics.profit_factor != float("inf")
            else 0.0
        )
        total_profit_improvement = (
            active_metrics.total_profit - passive_metrics.total_profit
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            active_metrics, passive_metrics, win_rate_improvement
        )

        result = ComparisonResult(
            active_metrics=active_metrics,
            passive_metrics=passive_metrics,
            win_rate_improvement=win_rate_improvement,
            profit_factor_improvement=profit_factor_improvement,
            total_profit_improvement=total_profit_improvement,
            action_effectiveness=list(self._action_effectiveness.values()),
            recommendation=recommendation,
        )

        # Store comparison in database
        self._store_comparison_result(result)

        logger.info(
            f"Performance comparison generated: "
            f"Win Rate Improvement: {win_rate_improvement:.2f}%, "
            f"Profit Factor Improvement: {profit_factor_improvement:.2f}, "
            f"Total Profit Improvement: {total_profit_improvement:.2f}"
        )

        return result

    def _generate_recommendation(
        self,
        active_metrics: PerformanceMetrics,
        passive_metrics: PerformanceMetrics,
        win_rate_improvement: float,
    ) -> str:
        """
        Generate recommendation based on comparison results.

        Args:
            active_metrics: Active management metrics
            passive_metrics: Passive management metrics
            win_rate_improvement: Win rate improvement percentage

        Returns:
            Human-readable recommendation
        """
        if win_rate_improvement >= 10.0:
            return (
                "Strong recommendation: Active management significantly outperforms "
                "passive management. Continue with current active management strategy."
            )
        elif win_rate_improvement >= 5.0:
            return (
                "Moderate recommendation: Active management shows clear benefits "
                "over passive management. Active management is recommended."
            )
        elif win_rate_improvement >= 0.0:
            return (
                "Weak recommendation: Active management shows marginal improvement. "
                "Consider optimizing management parameters."
            )
        else:
            return (
                "Not recommended: Active management underperforms passive management. "
                "Review and adjust management strategy."
            )

    def _store_comparison_result(self, result: ComparisonResult) -> None:
        """
        Store comparison result in database.

        Args:
            result: ComparisonResult to store
        """
        if self._connection is None:
            logger.warning("Database connection not available, comparison not stored")
            return

        try:
            cursor = self._connection.cursor()

            comparison_date = datetime.utcnow().date().isoformat()

            cursor.execute("""
                INSERT INTO performance_comparisons (
                    comparison_date, active_win_rate, passive_win_rate,
                    active_profit_factor, passive_profit_factor,
                    active_total_profit, passive_total_profit,
                    win_rate_improvement, profit_factor_improvement,
                    total_profit_improvement, active_total_trades, passive_total_trades,
                    summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comparison_date,
                result.active_metrics.win_rate,
                result.passive_metrics.win_rate,
                result.active_metrics.profit_factor,
                result.passive_metrics.profit_factor,
                result.active_metrics.total_profit,
                result.passive_metrics.total_profit,
                result.win_rate_improvement,
                result.profit_factor_improvement,
                result.total_profit_improvement,
                result.active_metrics.total_trades,
                result.passive_metrics.total_trades,
                result.recommendation,
            ))

            self._connection.commit()

            logger.debug(f"Comparison result stored for date: {comparison_date}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store comparison result: {e}")

    def get_action_effectiveness(
        self, action_type: ManagementActionType
    ) -> ActionEffectiveness:
        """
        Get effectiveness metrics for a specific action.

        Args:
            action_type: Type of management action

        Returns:
            ActionEffectiveness metrics
        """
        return self._action_effectiveness.get(action_type, ActionEffectiveness(action_type))

    def generate_comparison_report(self) -> str:
        """
        Generate a detailed performance comparison report.

        Returns:
            Formatted report string
        """
        comparison = self.compare_performance()

        lines = [
            "=" * 80,
            "ACTIVE VS PASSIVE MANAGEMENT PERFORMANCE REPORT",
            "=" * 80,
            "",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "SUMMARY",
            "-" * 80,
            f"Total Trades Analyzed: {comparison.active_metrics.total_trades}",
            f"Win Rate Improvement: {comparison.win_rate_improvement:+.2f}%",
            f"Profit Factor Improvement: {comparison.profit_factor_improvement:+.2f}",
            f"Total Profit Improvement: {comparison.total_profit_improvement:+.2f}",
            "",
            "ACTIVE MANAGEMENT METRICS",
            "-" * 80,
            f"Win Rate: {comparison.active_metrics.win_rate:.2f}%",
            f"Profit Factor: {comparison.active_metrics.profit_factor:.2f}",
            f"Total Profit: {comparison.active_metrics.total_profit:.2f}",
            f"Total Loss: {comparison.active_metrics.total_loss:.2f}",
            f"Average Win: {comparison.active_metrics.average_win:.2f}",
            f"Average Loss: {comparison.active_metrics.average_loss:.2f}",
            f"Max Drawdown: {comparison.active_metrics.max_drawdown:.2f}",
            f"Average Holding Time: {comparison.active_metrics.average_holding_time}",
            f"Best Trade: {comparison.active_metrics.best_trade:.2f}",
            f"Worst Trade: {comparison.active_metrics.worst_trade:.2f}",
            "",
            "PASSIVE (SET-AND-FORGET) METRICS",
            "-" * 80,
            f"Win Rate: {comparison.passive_metrics.win_rate:.2f}%",
            f"Profit Factor: {comparison.passive_metrics.profit_factor:.2f}",
            f"Total Profit: {comparison.passive_metrics.total_profit:.2f}",
            f"Total Loss: {comparison.passive_metrics.total_loss:.2f}",
            f"Average Win: {comparison.passive_metrics.average_win:.2f}",
            f"Average Loss: {comparison.passive_metrics.average_loss:.2f}",
            f"Max Drawdown: {comparison.passive_metrics.max_drawdown:.2f}",
            f"Average Holding Time: {comparison.passive_metrics.average_holding_time}",
            "",
            "MANAGEMENT ACTION EFFECTIVENESS",
            "-" * 80,
        ]

        for effectiveness in comparison.action_effectiveness:
            if effectiveness.times_triggered > 0:
                lines.extend([
                    f"{effectiveness.action_type.value}:",
                    f"  Times Triggered: {effectiveness.times_triggered}",
                    f"  Profit Saved: {effectiveness.profit_saved:.2f}",
                    f"  Loss Prevented: {effectiveness.loss_prevented:.2f}",
                    f"  Average Benefit: {effectiveness.average_benefit:.2f}",
                    f"  Success Rate: {effectiveness.success_rate:.2f}%",
                    "",
                ])

        lines.extend([
            "RECOMMENDATION",
            "-" * 80,
            comparison.recommendation,
            "",
            "=" * 80,
        ])

        report = "\n".join(lines)

        logger.info("Performance comparison report generated")

        return report

    def backtest_historical_data(
        self, historical_positions: list[dict[str, Any]]
    ) -> ComparisonResult:
        """
        Backtest active vs passive management on historical data.

        Args:
            historical_positions: List of historical position dictionaries containing:
                - ticket: int
                - symbol: str
                - direction: str
                - entry_price: float
                - exit_price: float
                - entry_time: datetime
                - exit_time: datetime
                - initial_stop_loss: float
                - initial_take_profit: float
                - final_profit: float
                - management_actions: list[str]
                - peak_profit: float
                - max_adverse_excursion: float

        Returns:
            ComparisonResult with backtest analysis
        """
        logger.info(
            f"Starting backtest on {len(historical_positions)} historical positions"
        )

        # Clear existing outcomes
        self._trade_outcomes.clear()

        # Process each historical position
        for pos_data in historical_positions:
            outcome = TradeOutcome(
                ticket=pos_data["ticket"],
                symbol=pos_data["symbol"],
                direction=pos_data["direction"],
                entry_price=pos_data["entry_price"],
                exit_price=pos_data["exit_price"],
                entry_time=pos_data["entry_time"],
                exit_time=pos_data["exit_time"],
                initial_stop_loss=pos_data.get("initial_stop_loss"),
                initial_take_profit=pos_data.get("initial_take_profit"),
                final_profit=pos_data["final_profit"],
                passive_profit=0.0,  # Will be calculated
                holding_time=timedelta(0),  # Will be calculated
                management_actions=pos_data.get("management_actions", []),
                peak_profit=pos_data.get("peak_profit", 0.0),
                max_adverse_excursion=pos_data.get("max_adverse_excursion", 0.0),
                volume=pos_data.get("volume", 1.0),
            )

            # Calculate holding time
            if outcome.exit_time:
                outcome.holding_time = outcome.exit_time - outcome.entry_time

            # Calculate passive profit
            outcome.passive_profit = self._calculate_passive_profit(
                position=TradePosition(
                    ticket=outcome.ticket,
                    symbol=outcome.symbol,
                    direction=outcome.direction,
                    entry_price=outcome.entry_price,
                    current_price=outcome.exit_price,
                    volume=outcome.volume,
                    stop_loss=outcome.initial_stop_loss,
                    take_profit=outcome.initial_take_profit,
                    entry_time=outcome.entry_time,
                    profit=0.0,
                    swap=0.0,
                    commission=0.0,
                ),
                exit_price=outcome.exit_price,
                peak_profit=outcome.peak_profit,
                max_adverse_excursion=outcome.max_adverse_excursion,
            )

            # Store outcome
            self._trade_outcomes.append(outcome)

        # Generate comparison
        result = self.compare_performance()

        logger.info(
            f"Backtest complete: Win rate improvement: {result.win_rate_improvement:.2f}%"
        )

        return result

    def get_trade_outcomes(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[TradeOutcome]:
        """
        Query trade outcomes from database.

        Args:
            symbol: Filter by symbol (optional)
            start_time: Filter by start time (optional)
            end_time: Filter by end time (optional)
            limit: Maximum number of outcomes to return (optional)

        Returns:
            List of TradeOutcome objects matching the criteria
        """
        outcomes = self._trade_outcomes

        # Apply filters
        if symbol is not None:
            outcomes = [o for o in outcomes if o.symbol == symbol]

        if start_time is not None:
            outcomes = [o for o in outcomes if o.entry_time >= start_time]

        if end_time is not None:
            outcomes = [o for o in outcomes if o.entry_time <= end_time]

        # Sort by entry time descending
        outcomes = sorted(outcomes, key=lambda o: o.entry_time, reverse=True)

        # Apply limit
        if limit is not None:
            outcomes = outcomes[:limit]

        return outcomes

    def clear_history(self) -> None:
        """Clear all comparison history from memory and database."""
        self._trade_outcomes.clear()

        # Reset action effectiveness
        for action_type in ManagementActionType:
            self._action_effectiveness[action_type] = ActionEffectiveness(
                action_type=action_type
            )

        # Clear from database
        if self._connection is not None:
            try:
                cursor = self._connection.cursor()
                cursor.execute("DELETE FROM trade_outcomes")
                cursor.execute("DELETE FROM performance_comparisons")
                cursor.execute("DELETE FROM action_effectiveness")
                self._connection.commit()
                logger.info("Cleared all performance comparison history from database")
            except sqlite3.Error as e:
                logger.error(f"Failed to clear history from database: {e}")

        logger.info("Cleared all performance comparison history from memory")

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        self.close()
