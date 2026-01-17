"""
Signal Decay Tracking System for EURABAY Living System.

This module provides signal decay tracking to monitor when signals lose
effectiveness over time (model decay) and ensure signal freshness.

Key Components:
- SignalDecayTracker class
- Signal age tracking and analysis
- Win rate calculation by age buckets
- Decay curve calculation
- Performance degradation monitoring
- Alerting for decayed signal sources
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import Signal, Trade, Configuration
from app.services.ensemble_signals import TradingSignal, SignalDirection


# ============================================================================
# Age Bucket Enum
# ============================================================================

class AgeBucket(str, Enum):
    """Signal age buckets for decay analysis."""
    BUCKET_0_5MIN = "0-5min"
    BUCKET_5_15MIN = "5-15min"
    BUCKET_15_30MIN = "15-30min"
    BUCKET_30_60MIN = "30-60min"
    BUCKET_60_PLUS = "60+min"


# ============================================================================
# Decay Data Structures
# ============================================================================

@dataclass
class AgeBucketStatistics:
    """
    Statistics for signals in a specific age bucket.

    Attributes:
        bucket: Age bucket range (e.g., "0-5min")
        total_signals: Total number of signals in this bucket
        winning_signals: Number of winning signals
        losing_signals: Number of losing signals
        win_rate: Actual win rate for signals in this bucket
        avg_age_minutes: Average age of signals in this bucket
        last_updated: When this bucket was last updated
    """
    bucket: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    avg_age_minutes: float
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bucket": self.bucket,
            "total_signals": self.total_signals,
            "winning_signals": self.winning_signals,
            "losing_signals": self.losing_signals,
            "win_rate": self.win_rate,
            "avg_age_minutes": self.avg_age_minutes,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class DecayCurve:
    """
    Signal effectiveness decay curve over time.

    Attributes:
        source_name: Name of the signal source
        symbol: Trading symbol
        bucket_statistics: Statistics for each age bucket
        decay_rate: Rate at which signal effectiveness decays per minute
        half_life_minutes: Time until signal effectiveness drops to 50%
        is_decayed: Whether signal shows significant decay (win rate drops > 20%)
        curve_generated: When the curve was generated
    """
    source_name: str
    symbol: str
    bucket_statistics: Dict[str, AgeBucketStatistics]
    decay_rate: float
    half_life_minutes: float
    is_decayed: bool
    curve_generated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_name": self.source_name,
            "symbol": self.symbol,
            "bucket_statistics": {
                bucket_name: stats.to_dict()
                for bucket_name, stats in self.bucket_statistics.items()
            },
            "decay_rate": self.decay_rate,
            "half_life_minutes": self.half_life_minutes,
            "is_decayed": self.is_decayed,
            "curve_generated": self.curve_generated.isoformat()
        }


@dataclass
class DecayReport:
    """
    Comprehensive decay report for a signal source.

    Attributes:
        source_name: Name of the signal source
        decay_curves: Decay curves for each symbol
        overall_decay_rate: Average decay rate across all symbols
        degraded_sources: List of sources with win rate < 50%
        total_signals_analyzed: Total number of signals analyzed
        report_generated: When the report was generated
    """
    source_name: str
    decay_curves: Dict[str, DecayCurve]
    overall_decay_rate: float
    degraded_sources: List[str]
    total_signals_analyzed: int
    report_generated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_name": self.source_name,
            "decay_curves": {
                symbol: curve.to_dict()
                for symbol, curve in self.decay_curves.items()
            },
            "overall_decay_rate": self.overall_decay_rate,
            "degraded_sources": self.degraded_sources,
            "total_signals_analyzed": self.total_signals_analyzed,
            "report_generated": self.report_generated.isoformat()
        }


@dataclass
class SourcePerformanceMetrics:
    """
    Performance metrics for a signal source over time.

    Attributes:
        source_name: Name of the signal source
        symbol: Trading symbol
        current_win_rate: Current win rate
        one_week_ago_win_rate: Win rate one week ago
        two_weeks_ago_win_rate: Win rate two weeks ago
        three_weeks_ago_win_rate: Win rate three weeks ago
        four_weeks_ago_win_rate: Win rate four weeks ago
        is_degraded: Whether win rate has dropped below 50%
        degradation_trend: Trend direction (improving, stable, declining)
        last_updated: When metrics were last updated
    """
    source_name: str
    symbol: str
    current_win_rate: float
    one_week_ago_win_rate: float
    two_weeks_ago_win_rate: float
    three_weeks_ago_win_rate: float
    four_weeks_ago_win_rate: float
    is_degraded: bool
    degradation_trend: str
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_name": self.source_name,
            "symbol": self.symbol,
            "current_win_rate": self.current_win_rate,
            "one_week_ago_win_rate": self.one_week_ago_win_rate,
            "two_weeks_ago_win_rate": self.two_weeks_ago_win_rate,
            "three_weeks_ago_win_rate": self.three_weeks_ago_win_rate,
            "four_weeks_ago_win_rate": self.four_weeks_ago_win_rate,
            "is_degraded": self.is_degraded,
            "degradation_trend": self.degradation_trend,
            "last_updated": self.last_updated.isoformat()
        }


# ============================================================================
# Signal Decay Tracker Class
# ============================================================================

class SignalDecayTracker:
    """
    Signal decay tracking system for monitoring signal effectiveness over time.

    This class tracks:
    1. Signal age (time since generation)
    2. Signal win rate by age buckets (0-5min, 5-15min, 15-30min, 30-60min, 60+min)
    3. Signal effectiveness decay curve
    4. Signal freshness check (reject signals older than 30 minutes)
    5. Performance degradation of signal sources over weeks
    6. Alerting if signal source win rate drops below 50%

    Example:
        tracker = SignalDecayTracker()

        # Check if signal is fresh enough
        is_fresh = tracker.is_signal_fresh(signal)

        # Get signal age
        age_minutes = tracker.get_signal_age(signal)

        # Calculate decay curve
        decay_curve = await tracker.calculate_decay_curve(
            db_session=session,
            source_name="xgboost_v10",
            symbol="V10"
        )

        # Generate decay report
        report = await tracker.generate_decay_report(
            db_session=session,
            source_name="xgboost_v10"
        )

    Attributes:
        max_signal_age_minutes: Maximum age for fresh signals (default: 30)
        min_samples_per_bucket: Minimum samples required for reliable statistics
        performance_cache: Cache of performance metrics
    """

    # Age bucket boundaries (in minutes)
    AGE_BUCKETS = {
        AgeBucket.BUCKET_0_5MIN: (0, 5),
        AgeBucket.BUCKET_5_15MIN: (5, 15),
        AgeBucket.BUCKET_15_30MIN: (15, 30),
        AgeBucket.BUCKET_30_60MIN: (30, 60),
        AgeBucket.BUCKET_60_PLUS: (60, float('inf'))
    }

    # Maximum signal age for freshness (30 minutes)
    DEFAULT_MAX_SIGNAL_AGE_MINUTES = 30

    # Minimum samples required for reliable statistics
    MIN_SAMPLES_PER_BUCKET = 20

    # Minimum win rate threshold (50%)
    MIN_WIN_RATE_THRESHOLD = 0.50

    def __init__(
        self,
        max_signal_age_minutes: int = DEFAULT_MAX_SIGNAL_AGE_MINUTES,
        min_samples_per_bucket: int = MIN_SAMPLES_PER_BUCKET
    ):
        """
        Initialize the signal decay tracker.

        Args:
            max_signal_age_minutes: Maximum age for fresh signals (default: 30)
            min_samples_per_bucket: Minimum samples required for reliable statistics
        """
        if max_signal_age_minutes < 1:
            raise ValueError(
                f"max_signal_age_minutes must be at least 1, got {max_signal_age_minutes}"
            )

        if min_samples_per_bucket < 1:
            raise ValueError(
                f"min_samples_per_bucket must be at least 1, got {min_samples_per_bucket}"
            )

        self.max_signal_age_minutes = max_signal_age_minutes
        self.min_samples_per_bucket = min_samples_per_bucket

        # Performance cache: {source_name: {symbol: SourcePerformanceMetrics}}
        self.performance_cache: Dict[str, Dict[str, SourcePerformanceMetrics]] = {}

        # Decay curve cache: {source_name: {symbol: DecayCurve}}
        self.decay_curve_cache: Dict[str, Dict[str, DecayCurve]] = {}

        # Cache timestamp: {source_name: last_update}
        self.cache_timestamp: Dict[str, datetime] = {}

        logger.info(
            f"SignalDecayTracker initialized: max_age={max_signal_age_minutes}min, "
            f"min_samples={min_samples_per_bucket}"
        )

    # ========================================================================
    # Signal Age Tracking
    # ========================================================================

    def get_signal_age(self, signal: TradingSignal) -> float:
        """
        Get the age of a signal in minutes.

        Args:
            signal: TradingSignal to check

        Returns:
            Signal age in minutes
        """
        age_seconds = (datetime.now() - signal.timestamp).total_seconds()
        age_minutes = age_seconds / 60.0
        return age_minutes

    def get_age_bucket(self, age_minutes: float) -> Optional[AgeBucket]:
        """
        Get the age bucket for a given signal age.

        Args:
            age_minutes: Signal age in minutes

        Returns:
            AgeBucket if age is in range, None otherwise
        """
        for bucket_name, (lower, upper) in self.AGE_BUCKETS.items():
            if lower <= age_minutes < upper:
                return bucket_name

        # Handle edge case for 60+ minutes
        if age_minutes >= 60:
            return AgeBucket.BUCKET_60_PLUS

        return None

    def is_signal_fresh(self, signal: TradingSignal) -> bool:
        """
        Check if a signal is fresh enough to use.

        Signals older than max_signal_age_minutes are considered stale
        and should be rejected.

        Args:
            signal: TradingSignal to check

        Returns:
            True if signal is fresh, False otherwise
        """
        age_minutes = self.get_signal_age(signal)
        is_fresh = age_minutes <= self.max_signal_age_minutes

        if not is_fresh:
            logger.debug(
                f"Signal from {signal.source} is stale: {age_minutes:.1f}min old "
                f"(max: {self.max_signal_age_minutes}min)"
            )

        return is_fresh

    def should_discard_signal(self, signal: TradingSignal) -> bool:
        """
        Check if a signal should be discarded due to decay.

        This is the main filtering method that combines age and freshness checks.

        Args:
            signal: TradingSignal to evaluate

        Returns:
            True if signal should be discarded, False otherwise
        """
        return not self.is_signal_fresh(signal)

    # ========================================================================
    # Win Rate by Age Buckets
    # ========================================================================

    async def get_age_bucket_statistics(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str,
        bucket: AgeBucket
    ) -> AgeBucketStatistics:
        """
        Calculate statistics for signals in a specific age bucket.

        This method queries the database for all signals from the given source
        within the age bucket range and calculates win rate based on trade outcomes.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol
            bucket: Age bucket to analyze

        Returns:
            AgeBucketStatistics containing the bucket's performance data
        """
        lower_bound, upper_bound = self.AGE_BUCKETS[bucket]

        # Calculate time ranges for the bucket
        # We need to find signals that were executed within this age range
        # This is complex because we need to know the time between signal generation
        # and trade execution

        # For simplicity, we'll use signal timestamp and estimate age
        # In production, you'd store the execution delay

        cutoff_date = datetime.now() - timedelta(days=30)  # Last 30 days of data

        if bucket == AgeBucket.BUCKET_60_PLUS:
            # 60+ minutes old
            max_delay = timedelta(hours=24)
        else:
            max_delay = timedelta(minutes=upper_bound)

        min_delay = timedelta(minutes=lower_bound)

        # Query signals with associated trades
        # We estimate age by looking at time difference between signal timestamp
        # and trade entry time
        query = (
            select(Signal, Trade)
            .join(Trade, Signal.trade_id == Trade.id)
            .where(
                and_(
                    Signal.strategy == source_name,
                    Signal.symbol == symbol,
                    Signal.timestamp >= cutoff_date,
                    Trade.status == "CLOSED",
                    Trade.entry_time >= Signal.timestamp + min_delay,
                    Trade.entry_time <= Signal.timestamp + max_delay
                )
            )
        )

        result = await db_session.execute(query)
        signal_trade_pairs = result.all()

        # Calculate statistics
        total_signals = len(signal_trade_pairs)
        winning_signals = sum(
            1 for signal, trade in signal_trade_pairs
            if trade.profit_loss and trade.profit_loss > 0
        )
        losing_signals = total_signals - winning_signals

        win_rate = winning_signals / total_signals if total_signals > 0 else 0.0

        # Calculate average age
        ages = []
        for signal, trade in signal_trade_pairs:
            age_minutes = (trade.entry_time - signal.timestamp).total_seconds() / 60.0
            ages.append(age_minutes)

        avg_age_minutes = sum(ages) / len(ages) if ages else 0.0

        statistics = AgeBucketStatistics(
            bucket=bucket.value,
            total_signals=total_signals,
            winning_signals=winning_signals,
            losing_signals=losing_signals,
            win_rate=win_rate,
            avg_age_minutes=avg_age_minutes,
            last_updated=datetime.now()
        )

        logger.debug(
            f"Age bucket {bucket.value} for {source_name}/{symbol}: "
            f"win_rate={win_rate:.2%}, n={total_signals}, avg_age={avg_age_minutes:.1f}min"
        )

        return statistics

    async def calculate_decay_curve(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str
    ) -> DecayCurve:
        """
        Calculate the signal effectiveness decay curve.

        This method calculates statistics for all age buckets and determines
        the rate at which signal effectiveness decays over time.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol

        Returns:
            DecayCurve containing comprehensive decay analysis
        """
        logger.info(
            f"Calculating decay curve for {source_name} on {symbol}"
        )

        bucket_statistics = {}

        # Calculate statistics for each bucket
        for bucket_name in AgeBucket:
            stats = await self.get_age_bucket_statistics(
                db_session, source_name, symbol, bucket_name
            )
            bucket_statistics[bucket_name.value] = stats

        # Calculate decay rate
        # We fit a simple linear model to the win rates
        decay_rate = await self._calculate_decay_rate(bucket_statistics)

        # Calculate half-life (time until win rate drops to 50% of initial)
        # Using exponential decay model: win_rate = initial * exp(-decay_rate * time)
        # half_life = ln(0.5) / decay_rate
        if decay_rate > 0:
            half_life_minutes = abs(0.693 / decay_rate)  # ln(0.5) ≈ -0.693
        else:
            half_life_minutes = float('inf')  # No decay

        # Check if signal shows significant decay
        # Significant decay = win rate drops more than 20% from freshest to oldest bucket
        initial_win_rate = bucket_statistics.get(
            AgeBucket.BUCKET_0_5MIN.value,
            AgeBucketStatistics(
                bucket="0-5min",
                total_signals=0,
                winning_signals=0,
                losing_signals=0,
                win_rate=0.0,
                avg_age_minutes=0.0,
                last_updated=datetime.now()
            )
        ).win_rate

        final_win_rate = bucket_statistics.get(
            AgeBucket.BUCKET_60_PLUS.value,
            AgeBucketStatistics(
                bucket="60+min",
                total_signals=0,
                winning_signals=0,
                losing_signals=0,
                win_rate=0.0,
                avg_age_minutes=0.0,
                last_updated=datetime.now()
            )
        ).win_rate

        decay_percentage = initial_win_rate - final_win_rate
        is_decayed = decay_percentage > 0.20  # 20% decay threshold

        decay_curve = DecayCurve(
            source_name=source_name,
            symbol=symbol,
            bucket_statistics=bucket_statistics,
            decay_rate=decay_rate,
            half_life_minutes=half_life_minutes,
            is_decayed=is_decayed,
            curve_generated=datetime.now()
        )

        # Update cache
        if source_name not in self.decay_curve_cache:
            self.decay_curve_cache[source_name] = {}
        self.decay_curve_cache[source_name][symbol] = decay_curve
        self.cache_timestamp[source_name] = datetime.now()

        logger.info(
            f"Decay curve calculated for {source_name}/{symbol}: "
            f"decay_rate={decay_rate:.4f}/min, half_life={half_life_minutes:.1f}min, "
            f"is_decayed={is_decayed}"
        )

        return decay_curve

    async def _calculate_decay_rate(
        self,
        bucket_statistics: Dict[str, AgeBucketStatistics]
    ) -> float:
        """
        Calculate the decay rate from bucket statistics.

        Uses simple linear regression on win rates vs average age.

        Args:
            bucket_statistics: Statistics for each age bucket

        Returns:
            Decay rate (win rate change per minute)
        """
        # Filter buckets with sufficient data
        valid_buckets = [
            (stats.avg_age_minutes, stats.win_rate)
            for stats in bucket_statistics.values()
            if stats.total_signals >= self.min_samples_per_bucket
        ]

        if len(valid_buckets) < 2:
            logger.warning("Not enough valid buckets for decay rate calculation")
            return 0.0

        # Simple linear regression: y = mx + b
        # where y = win_rate, x = age_minutes
        # m = decay_rate

        n = len(valid_buckets)
        sum_x = sum(age for age, _ in valid_buckets)
        sum_y = sum(win_rate for _, win_rate in valid_buckets)
        sum_xy = sum(age * win_rate for age, win_rate in valid_buckets)
        sum_x2 = sum(age ** 2 for age, _ in valid_buckets)

        # Calculate slope (decay rate)
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0

        decay_rate = (n * sum_xy - sum_x * sum_y) / denominator

        return decay_rate

    # ========================================================================
    # Performance Degradation Tracking
    # ========================================================================

    async def get_source_performance_metrics(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str
    ) -> SourcePerformanceMetrics:
        """
        Get performance metrics for a signal source over time.

        Tracks win rate over the past 4 weeks to detect degradation.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol

        Returns:
            SourcePerformanceMetrics containing weekly performance data
        """
        logger.debug(
            f"Getting performance metrics for {source_name} on {symbol}"
        )

        # Calculate win rates for different time periods
        current_win_rate = await self._calculate_win_rate_for_period(
            db_session, source_name, symbol, days=7
        )
        one_week_ago_win_rate = await self._calculate_win_rate_for_period(
            db_session, source_name, symbol, days=7, offset_weeks=1
        )
        two_weeks_ago_win_rate = await self._calculate_win_rate_for_period(
            db_session, source_name, symbol, days=7, offset_weeks=2
        )
        three_weeks_ago_win_rate = await self._calculate_win_rate_for_period(
            db_session, source_name, symbol, days=7, offset_weeks=3
        )
        four_weeks_ago_win_rate = await self._calculate_win_rate_for_period(
            db_session, source_name, symbol, days=7, offset_weeks=4
        )

        # Check if degraded
        is_degraded = current_win_rate < self.MIN_WIN_RATE_THRESHOLD

        # Determine trend
        if current_win_rate > one_week_ago_win_rate + 0.05:
            trend = "improving"
        elif current_win_rate < one_week_ago_win_rate - 0.05:
            trend = "declining"
        else:
            trend = "stable"

        metrics = SourcePerformanceMetrics(
            source_name=source_name,
            symbol=symbol,
            current_win_rate=current_win_rate,
            one_week_ago_win_rate=one_week_ago_win_rate,
            two_weeks_ago_win_rate=two_weeks_ago_win_rate,
            three_weeks_ago_win_rate=three_weeks_ago_win_rate,
            four_weeks_ago_win_rate=four_weeks_ago_win_rate,
            is_degraded=is_degraded,
            degradation_trend=trend,
            last_updated=datetime.now()
        )

        # Update cache
        if source_name not in self.performance_cache:
            self.performance_cache[source_name] = {}
        self.performance_cache[source_name][symbol] = metrics

        logger.debug(
            f"Performance metrics for {source_name}/{symbol}: "
            f"current={current_win_rate:.2%}, trend={trend}, "
            f"degraded={is_degraded}"
        )

        return metrics

    async def _calculate_win_rate_for_period(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str,
        days: int = 7,
        offset_weeks: int = 0
    ) -> float:
        """
        Calculate win rate for a specific time period.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol
            days: Number of days in the period
            offset_weeks: Number of weeks to offset (0 = current, 1 = 1 week ago, etc.)

        Returns:
            Win rate for the period
        """
        # Calculate date range
        end_date = datetime.now() - timedelta(weeks=offset_weeks)
        start_date = end_date - timedelta(days=days)

        # Query trades for this period
        query = (
            select(Trade)
            .join(Signal, Signal.trade_id == Trade.id)
            .where(
                and_(
                    Signal.strategy == source_name,
                    Signal.symbol == symbol,
                    Signal.timestamp >= start_date,
                    Signal.timestamp < end_date,
                    Trade.status == "CLOSED"
                )
            )
        )

        result = await db_session.execute(query)
        trades = result.scalars().all()

        if not trades:
            return 0.50  # Default to 50% if no data

        winning_trades = sum(1 for t in trades if t.profit_loss and t.profit_loss > 0)
        win_rate = winning_trades / len(trades)

        return win_rate

    async def check_for_degraded_sources(
        self,
        db_session: AsyncSession,
        source_names: List[str],
        symbols: List[str]
    ) -> List[str]:
        """
        Check for degraded signal sources and return list of alerts.

        A source is considered degraded if its win rate drops below 50%.

        Args:
            db_session: Database session
            source_names: List of signal source names to check
            symbols: List of symbols to check

        Returns:
            List of alert messages for degraded sources
        """
        alerts = []

        for source_name in source_names:
            for symbol in symbols:
                metrics = await self.get_source_performance_metrics(
                    db_session, source_name, symbol
                )

                if metrics.is_degraded:
                    alert = (
                        f"DEGRADED SOURCE: {source_name} on {symbol} | "
                        f"Current win rate: {metrics.current_win_rate:.2%} | "
                        f"Trend: {metrics.degradation_trend} | "
                        f"Below threshold: {self.MIN_WIN_RATE_THRESHOLD:.2%}"
                    )
                    alerts.append(alert)
                    logger.warning(alert)

        return alerts

    # ========================================================================
    # Decay Report Generation
    # ========================================================================

    async def generate_decay_report(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbols: Optional[List[str]] = None
    ) -> DecayReport:
        """
        Generate a comprehensive decay report for a signal source.

        The report includes:
        - Decay curves for each symbol
        - Overall decay rate
        - List of degraded sources
        - Total signals analyzed

        Args:
            db_session: Database session
            source_name: Signal source to generate report for
            symbols: List of symbols to analyze (default: common symbols)

        Returns:
            DecayReport containing comprehensive decay analysis
        """
        logger.info(f"Generating decay report for: {source_name}")

        # Default symbols if not provided
        if symbols is None:
            symbols = ["V10", "V25", "V50", "V75", "V100"]

        decay_curves = {}
        total_signals = 0
        decay_rates = []

        # Calculate decay curves for each symbol
        for symbol in symbols:
            try:
                curve = await self.calculate_decay_curve(
                    db_session, source_name, symbol
                )
                decay_curves[symbol] = curve

                # Sum total signals
                total_signals += sum(
                    stats.total_signals
                    for stats in curve.bucket_statistics.values()
                )

                # Collect decay rates
                if curve.decay_rate != 0:
                    decay_rates.append(abs(curve.decay_rate))

            except Exception as e:
                logger.error(
                    f"Error calculating decay curve for {source_name}/{symbol}: {e}"
                )
                continue

        # Calculate overall decay rate
        overall_decay_rate = (
            sum(decay_rates) / len(decay_rates)
            if decay_rates else 0.0
        )

        # Check for degraded sources
        degraded = []
        for symbol, curve in decay_curves.items():
            if curve.is_decayed:
                degraded.append(f"{source_name}/{symbol}")

        report = DecayReport(
            source_name=source_name,
            decay_curves=decay_curves,
            overall_decay_rate=overall_decay_rate,
            degraded_sources=degraded,
            total_signals_analyzed=total_signals,
            report_generated=datetime.now()
        )

        logger.info(
            f"Decay report generated for {source_name}: "
            f"overall_decay={overall_decay_rate:.4f}, "
            f"degraded={len(degraded)}, signals={total_signals}"
        )

        return report

    # ========================================================================
    # Database Persistence
    # ========================================================================

    async def store_decay_data(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str
    ) -> None:
        """
        Store decay data in the database for persistence.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol
        """
        # Get decay curve
        decay_curve = self.decay_curve_cache.get(source_name, {}).get(symbol)
        if decay_curve is None:
            logger.warning(f"No decay curve data found for {source_name}/{symbol}")
            return

        # Serialize to JSON
        decay_data = {
            "decay_curve": decay_curve.to_dict(),
            "last_updated": datetime.now().isoformat()
        }

        # Check if configuration exists
        config_key = f"decay_{source_name}_{symbol}"
        query = select(Configuration).where(Configuration.config_key == config_key)
        result = await db_session.execute(query)
        existing_config = result.scalar_one_or_none()

        if existing_config:
            # Update existing configuration
            existing_config.config_value = json.dumps(decay_data)
            existing_config.updated_at = datetime.now()
        else:
            # Create new configuration
            new_config = Configuration(
                config_key=config_key,
                config_value=json.dumps(decay_data),
                description=f"Decay tracking data for {source_name} on {symbol}",
                category="decay_tracking",
                is_active=True
            )
            db_session.add(new_config)

        await db_session.commit()

        logger.info(f"Stored decay data for {source_name}/{symbol} in database")

    async def load_decay_data(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str
    ) -> bool:
        """
        Load decay data from the database.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol

        Returns:
            True if decay data was loaded successfully, False otherwise
        """
        config_key = f"decay_{source_name}_{symbol}"
        query = select(Configuration).where(Configuration.config_key == config_key)
        result = await db_session.execute(query)
        config = result.scalar_one_or_none()

        if config is None:
            logger.info(f"No decay data found for {source_name}/{symbol}")
            return False

        try:
            data = json.loads(config.config_value)

            # Restore decay curve
            curve_dict = data.get("decay_curve", {})
            decay_curve = DecayCurve(
                source_name=curve_dict["source_name"],
                symbol=curve_dict["symbol"],
                bucket_statistics={
                    bucket: AgeBucketStatistics(
                        bucket=stats["bucket"],
                        total_signals=stats["total_signals"],
                        winning_signals=stats["winning_signals"],
                        losing_signals=stats["losing_signals"],
                        win_rate=stats["win_rate"],
                        avg_age_minutes=stats["avg_age_minutes"],
                        last_updated=datetime.fromisoformat(stats["last_updated"])
                    )
                    for bucket, stats in curve_dict["bucket_statistics"].items()
                },
                decay_rate=curve_dict["decay_rate"],
                half_life_minutes=curve_dict["half_life_minutes"],
                is_decayed=curve_dict["is_decayed"],
                curve_generated=datetime.fromisoformat(curve_dict["curve_generated"])
            )

            # Update cache
            if source_name not in self.decay_curve_cache:
                self.decay_curve_cache[source_name] = {}
            self.decay_curve_cache[source_name][symbol] = decay_curve
            self.cache_timestamp[source_name] = datetime.fromisoformat(data["last_updated"])

            logger.info(f"Loaded decay data for {source_name}/{symbol} from database")
            return True

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load decay data for {source_name}/{symbol}: {e}")
            return False

    # ========================================================================
    # Cache Management
    # ========================================================================

    def clear_cache(self, source_name: Optional[str] = None) -> None:
        """
        Clear the cache.

        Args:
            source_name: If provided, only clear cache for this source.
                       Otherwise, clear all cache.
        """
        if source_name:
            self.performance_cache.pop(source_name, None)
            self.decay_curve_cache.pop(source_name, None)
            self.cache_timestamp.pop(source_name, None)
            logger.debug(f"Cleared cache for {source_name}")
        else:
            self.performance_cache.clear()
            self.decay_curve_cache.clear()
            self.cache_timestamp.clear()
            logger.debug("Cleared all cache")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_decay_tracker(
    max_signal_age_minutes: int = SignalDecayTracker.DEFAULT_MAX_SIGNAL_AGE_MINUTES,
    min_samples_per_bucket: int = SignalDecayTracker.MIN_SAMPLES_PER_BUCKET
) -> SignalDecayTracker:
    """
    Create and configure a signal decay tracker.

    Args:
        max_signal_age_minutes: Maximum age for fresh signals
        min_samples_per_bucket: Minimum samples required for reliable statistics

    Returns:
        Configured SignalDecayTracker instance
    """
    tracker = SignalDecayTracker(
        max_signal_age_minutes=max_signal_age_minutes,
        min_samples_per_bucket=min_samples_per_bucket
    )
    logger.info("Created new SignalDecayTracker")
    return tracker


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "AgeBucket",
    "AgeBucketStatistics",
    "DecayCurve",
    "DecayReport",
    "SourcePerformanceMetrics",
    "SignalDecayTracker",
    "create_decay_tracker"
]
