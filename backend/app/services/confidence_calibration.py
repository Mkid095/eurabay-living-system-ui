"""
Confidence Calibration System for EURABAY Living System.

This module provides confidence calibration for trading signals to ensure
that predicted confidence matches actual win rates.

Key Components:
- ConfidenceCalibrator class
- Confidence bin tracking and analysis
- Calibration error calculation
- Weekly calibration updates
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import Signal, Trade


# ============================================================================
# Confidence Bin Enum
# ============================================================================

class ConfidenceBin(str, Enum):
    """Confidence bin ranges for calibration."""
    BIN_50_60 = "50-60%"
    BIN_60_70 = "60-70%"
    BIN_70_80 = "70-80%"
    BIN_80_90 = "80-90%"
    BIN_90_100 = "90-100%"


# ============================================================================
# Calibration Data Structures
# ============================================================================

@dataclass
class BinStatistics:
    """
    Statistics for a confidence bin.

    Attributes:
        bin_range: Confidence bin range (e.g., "50-60%")
        predicted_confidence: Average predicted confidence for this bin
        actual_win_rate: Actual win rate for signals in this bin
        calibration_error: Absolute difference between predicted and actual
        total_signals: Total number of signals in this bin
        winning_signals: Number of winning signals
        losing_signals: Number of losing signals
        last_updated: When this bin was last updated
    """
    bin_range: str
    predicted_confidence: float
    actual_win_rate: float
    calibration_error: float
    total_signals: int
    winning_signals: int
    losing_signals: int
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bin_range": self.bin_range,
            "predicted_confidence": self.predicted_confidence,
            "actual_win_rate": self.actual_win_rate,
            "calibration_error": self.calibration_error,
            "total_signals": self.total_signals,
            "winning_signals": self.winning_signals,
            "losing_signals": self.losing_signals,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class CalibrationReport:
    """
    Full calibration report for a signal source.

    Attributes:
        source_name: Name of the signal source
        bin_statistics: Statistics for each confidence bin
        overall_calibration_error: Average calibration error across all bins
        total_signals_calibrated: Total number of signals used for calibration
        is_well_calibrated: Whether calibration error < 5% for all bins
        report_generated: When the report was generated
    """
    source_name: str
    bin_statistics: Dict[str, BinStatistics]
    overall_calibration_error: float
    total_signals_calibrated: int
    is_well_calibrated: bool
    report_generated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_name": self.source_name,
            "bin_statistics": {
                bin_name: stats.to_dict()
                for bin_name, stats in self.bin_statistics.items()
            },
            "overall_calibration_error": self.overall_calibration_error,
            "total_signals_calibrated": self.total_signals_calibrated,
            "is_well_calibrated": self.is_well_calibrated,
            "report_generated": self.report_generated.isoformat()
        }


# ============================================================================
# Confidence Calibrator Class
# ============================================================================

class ConfidenceCalibrator:
    """
    Confidence calibration system for trading signals.

    This class tracks predicted confidence vs actual outcomes for each signal
    source and applies calibration adjustments to ensure that when the system
    says 70% confidence, it actually wins 70% of the time.

    Key Features:
    - Confidence bin tracking (50-60%, 60-70%, 70-80%, 80-90%, 90-100%)
    - Actual win rate calculation per bin
    - Calibration error calculation
    - Calibration adjustment application
    - Weekly calibration updates
    - Calibration report generation

    Example:
        calibrator = ConfidenceCalibrator()

        # Record a signal outcome
        await calibrator.record_signal_outcome(
            signal_id=123,
            predicted_confidence=0.75,
            actual_outcome=True,  # Win
            source_name="xgboost_v10",
            symbol="V10"
        )

        # Get calibrated confidence
        calibrated = await calibrator.get_calibrated_confidence(
            predicted_confidence=0.75,
            source_name="xgboost_v10"
        )

        # Generate calibration report
        report = await calibrator.generate_calibration_report("xgboost_v10")

    Attributes:
        calibration_cache: In-memory cache of calibration data
        min_samples_per_bin: Minimum samples required for reliable calibration
        calibration_update_frequency_days: How often to update calibration (weekly)
    """

    # Confidence bin boundaries
    BIN_RANGES = {
        ConfidenceBin.BIN_50_60: (0.50, 0.60),
        ConfidenceBin.BIN_60_70: (0.60, 0.70),
        ConfidenceBin.BIN_70_80: (0.70, 0.80),
        ConfidenceBin.BIN_80_90: (0.80, 0.90),
        ConfidenceBin.BIN_90_100: (0.90, 1.00)
    }

    # Maximum calibration age before requiring update (7 days)
    MAX_CALIBRATION_AGE_DAYS = 7

    # Minimum samples required for reliable calibration
    MIN_SAMPLES_PER_BIN = 20

    def __init__(
        self,
        min_samples_per_bin: int = 20,
        calibration_update_frequency_days: int = 7
    ):
        """
        Initialize the confidence calibrator.

        Args:
            min_samples_per_bin: Minimum samples required for reliable calibration
            calibration_update_frequency_days: How often to update calibration
        """
        self.min_samples_per_bin = min_samples_per_bin
        self.calibration_update_frequency_days = calibration_update_frequency_days

        # In-memory cache of calibration data: {source_name: {bin_range: calibrated_confidence}}
        self.calibration_cache: Dict[str, Dict[str, float]] = {}

        # Cache of bin statistics: {source_name: {bin_range: BinStatistics}}
        self.bin_statistics_cache: Dict[str, Dict[str, BinStatistics]] = {}

        # Track last calibration update: {source_name: last_update_timestamp}
        self.last_calibration_update: Dict[str, datetime] = {}

        logger.info(
            f"ConfidenceCalibrator initialized: min_samples={min_samples_per_bin}, "
            f"update_frequency={calibration_update_frequency_days} days"
        )

    def get_confidence_bin(self, confidence: float) -> Optional[ConfidenceBin]:
        """
        Get the confidence bin for a given confidence value.

        Args:
            confidence: Confidence value (0.0 to 1.0)

        Returns:
            ConfidenceBin if confidence is in range, None otherwise
        """
        for bin_name, (lower, upper) in self.BIN_RANGES.items():
            if lower <= confidence < upper:
                return bin_name

        # Handle edge case for 100% confidence
        if confidence >= 0.90:
            return ConfidenceBin.BIN_90_100

        return None

    async def get_bin_statistics(
        self,
        db_session: AsyncSession,
        source_name: str,
        bin_range: ConfidenceBin
    ) -> BinStatistics:
        """
        Calculate statistics for a specific confidence bin.

        This method queries the database for all signals from the given source
        within the confidence bin range and calculates:
        - Total signals
        - Winning signals
        - Actual win rate
        - Calibration error

        Args:
            db_session: Database session
            source_name: Signal source name
            bin_range: Confidence bin to analyze

        Returns:
            BinStatistics containing the bin's performance data
        """
        lower, upper = self.BIN_RANGES[bin_range]

        # Calculate cutoff date for weekly data
        cutoff_date = datetime.now() - timedelta(days=self.calibration_update_frequency_days * 4)  # 4 weeks of data

        # Query signals within this bin range that have associated trades
        query = (
            select(Signal, Trade)
            .join(Trade, Signal.trade_id == Trade.id)
            .where(
                and_(
                    Signal.strategy == source_name,
                    Signal.confidence >= lower,
                    Signal.confidence < upper,
                    Signal.timestamp >= cutoff_date,
                    Trade.status == "CLOSED"
                )
            )
        )

        result = await db_session.execute(query)
        signal_trade_pairs = result.all()

        # Calculate statistics
        total_signals = len(signal_trade_pairs)
        winning_signals = sum(1 for signal, trade in signal_trade_pairs if trade.profit_loss and trade.profit_loss > 0)
        losing_signals = total_signals - winning_signals

        actual_win_rate = winning_signals / total_signals if total_signals > 0 else 0.0
        predicted_confidence = (lower + upper) / 2
        calibration_error = abs(predicted_confidence - actual_win_rate)

        statistics = BinStatistics(
            bin_range=bin_range.value,
            predicted_confidence=predicted_confidence,
            actual_win_rate=actual_win_rate,
            calibration_error=calibration_error,
            total_signals=total_signals,
            winning_signals=winning_signals,
            losing_signals=losing_signals,
            last_updated=datetime.now()
        )

        logger.debug(
            f"Bin {bin_range.value} for {source_name}: "
            f"predicted={predicted_confidence:.2%}, actual={actual_win_rate:.2%}, "
            f"error={calibration_error:.2%}, n={total_signals}"
        )

        return statistics

    async def update_calibration(
        self,
        db_session: AsyncSession,
        source_name: str
    ) -> None:
        """
        Update calibration data for a signal source.

        This method calculates bin statistics for all confidence bins and
        updates the calibration cache with the latest calibration adjustments.

        Args:
            db_session: Database session
            source_name: Signal source to calibrate
        """
        logger.info(f"Updating calibration for signal source: {source_name}")

        bin_stats = {}
        calibration_adjustments = {}

        # Calculate statistics for each bin
        for bin_name in ConfidenceBin:
            stats = await self.get_bin_statistics(db_session, source_name, bin_name)
            bin_stats[bin_name.value] = stats

            # Calculate calibration adjustment
            # If predicted is 70% but actual is 60%, adjust down to 60%
            if stats.total_signals >= self.min_samples_per_bin:
                calibrated_confidence = stats.actual_win_rate
            else:
                # Not enough samples, use predicted confidence (no adjustment)
                calibrated_confidence = stats.predicted_confidence

            calibration_adjustments[bin_name.value] = calibrated_confidence

        # Update caches
        self.bin_statistics_cache[source_name] = bin_stats
        self.calibration_cache[source_name] = calibration_adjustments
        self.last_calibration_update[source_name] = datetime.now()

        logger.info(
            f"Calibration updated for {source_name}: "
            f"{len(bin_stats)} bins calibrated"
        )

    async def get_calibrated_confidence(
        self,
        db_session: AsyncSession,
        predicted_confidence: float,
        source_name: str
    ) -> float:
        """
        Get calibrated confidence for a prediction.

        If calibration data exists and is recent, returns the calibrated
        confidence based on historical performance. Otherwise, returns
        the predicted confidence without adjustment.

        Args:
            db_session: Database session
            predicted_confidence: Predicted confidence (0.0 to 1.0)
            source_name: Signal source name

        Returns:
            Calibrated confidence score
        """
        # Get the bin for this confidence
        bin_name = self.get_confidence_bin(predicted_confidence)

        if bin_name is None:
            logger.warning(
                f"Confidence {predicted_confidence:.2%} not in any bin range, "
                f"returning predicted confidence"
            )
            return predicted_confidence

        # Check if calibration exists and is recent
        last_update = self.last_calibration_update.get(source_name)
        needs_update = (
            last_update is None or
            (datetime.now() - last_update).days > self.calibration_update_frequency_days
        )

        if needs_update:
            logger.info(f"Calibration data stale or missing for {source_name}, updating...")
            await self.update_calibration(db_session, source_name)

        # Get calibrated confidence from cache
        source_calibration = self.calibration_cache.get(source_name, {})
        calibrated = source_calibration.get(bin_name.value, predicted_confidence)

        logger.debug(
            f"Calibrated confidence for {source_name}: "
            f"predicted={predicted_confidence:.2%}, calibrated={calibrated:.2%}"
        )

        return calibrated

    async def generate_calibration_report(
        self,
        db_session: AsyncSession,
        source_name: str
    ) -> CalibrationReport:
        """
        Generate a comprehensive calibration report for a signal source.

        The report includes:
        - Statistics for each confidence bin
        - Overall calibration error
        - Whether the source is well calibrated (error < 5% for all bins)
        - Total signals used for calibration

        Args:
            db_session: Database session
            source_name: Signal source to generate report for

        Returns:
            CalibrationReport containing comprehensive calibration data
        """
        logger.info(f"Generating calibration report for: {source_name}")

        # Ensure calibration is up to date
        await self.update_calibration(db_session, source_name)

        # Get bin statistics from cache
        bin_stats = self.bin_statistics_cache.get(source_name, {})

        # Calculate overall calibration error
        calibration_errors = [
            stats.calibration_error
            for stats in bin_stats.values()
            if stats.total_signals >= self.min_samples_per_bin
        ]

        overall_error = (
            sum(calibration_errors) / len(calibration_errors)
            if calibration_errors else 0.0
        )

        # Check if well calibrated (error < 5% for all bins)
        is_well_calibrated = all(
            stats.calibration_error < 0.05
            for stats in bin_stats.values()
            if stats.total_signals >= self.min_samples_per_bin
        )

        # Calculate total signals calibrated
        total_signals = sum(
            stats.total_signals
            for stats in bin_stats.values()
        )

        report = CalibrationReport(
            source_name=source_name,
            bin_statistics=bin_stats,
            overall_calibration_error=overall_error,
            total_signals_calibrated=total_signals,
            is_well_calibrated=is_well_calibrated,
            report_generated=datetime.now()
        )

        logger.info(
            f"Calibration report generated for {source_name}: "
            f"overall_error={overall_error:.2%}, well_calibrated={is_well_calibrated}"
        )

        return report

    async def store_calibration_data(
        self,
        db_session: AsyncSession,
        source_name: str
    ) -> None:
        """
        Store calibration data in the database for persistence.

        This method serializes the calibration data and stores it in the
        configurations table for persistence across restarts.

        Args:
            db_session: Database session
            source_name: Signal source name
        """
        from app.models.models import Configuration

        # Get calibration data
        bin_stats = self.bin_statistics_cache.get(source_name, {})
        calibration_adjustments = self.calibration_cache.get(source_name, {})

        # Serialize to JSON
        calibration_data = {
            "bin_statistics": {
                bin_name: stats.to_dict()
                for bin_name, stats in bin_stats.items()
            },
            "calibration_adjustments": calibration_adjustments,
            "last_updated": self.last_calibration_update.get(source_name, datetime.now()).isoformat()
        }

        # Check if configuration exists
        query = select(Configuration).where(
            Configuration.config_key == f"calibration_{source_name}"
        )
        result = await db_session.execute(query)
        existing_config = result.scalar_one_or_none()

        if existing_config:
            # Update existing configuration
            existing_config.config_value = json.dumps(calibration_data)
            existing_config.updated_at = datetime.now()
        else:
            # Create new configuration
            new_config = Configuration(
                config_key=f"calibration_{source_name}",
                config_value=json.dumps(calibration_data),
                description=f"Confidence calibration data for {source_name}",
                category="calibration",
                is_active=True
            )
            db_session.add(new_config)

        await db_session.commit()

        logger.info(f"Stored calibration data for {source_name} in database")

    async def load_calibration_data(
        self,
        db_session: AsyncSession,
        source_name: str
    ) -> bool:
        """
        Load calibration data from the database.

        Args:
            db_session: Database session
            source_name: Signal source name

        Returns:
            True if calibration data was loaded successfully, False otherwise
        """
        from app.models.models import Configuration

        query = select(Configuration).where(
            Configuration.config_key == f"calibration_{source_name}"
        )
        result = await db_session.execute(query)
        config = result.scalar_one_or_none()

        if config is None:
            logger.info(f"No calibration data found for {source_name}")
            return False

        try:
            data = json.loads(config.config_value)

            # Restore bin statistics
            bin_stats = {}
            for bin_name, stats_dict in data.get("bin_statistics", {}).items():
                bin_stats[bin_name] = BinStatistics(
                    bin_range=stats_dict["bin_range"],
                    predicted_confidence=stats_dict["predicted_confidence"],
                    actual_win_rate=stats_dict["actual_win_rate"],
                    calibration_error=stats_dict["calibration_error"],
                    total_signals=stats_dict["total_signals"],
                    winning_signals=stats_dict["winning_signals"],
                    losing_signals=stats_dict["losing_signals"],
                    last_updated=datetime.fromisoformat(stats_dict["last_updated"])
                )

            self.bin_statistics_cache[source_name] = bin_stats
            self.calibration_cache[source_name] = data.get("calibration_adjustments", {})
            self.last_calibration_update[source_name] = datetime.fromisoformat(data["last_updated"])

            logger.info(f"Loaded calibration data for {source_name} from database")
            return True

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load calibration data for {source_name}: {e}")
            return False

    def get_all_cached_sources(self) -> List[str]:
        """
        Get list of all signal sources with cached calibration data.

        Returns:
            List of source names with calibration data
        """
        return list(self.calibration_cache.keys())

    def clear_calibration_cache(self, source_name: Optional[str] = None) -> None:
        """
        Clear calibration cache.

        Args:
            source_name: If provided, only clear cache for this source.
                       Otherwise, clear all cache.
        """
        if source_name:
            self.calibration_cache.pop(source_name, None)
            self.bin_statistics_cache.pop(source_name, None)
            self.last_calibration_update.pop(source_name, None)
            logger.debug(f"Cleared calibration cache for {source_name}")
        else:
            self.calibration_cache.clear()
            self.bin_statistics_cache.clear()
            self.last_calibration_update.clear()
            logger.debug("Cleared all calibration cache")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_confidence_calibrator(
    min_samples_per_bin: int = 20,
    calibration_update_frequency_days: int = 7
) -> ConfidenceCalibrator:
    """
    Create and configure a confidence calibrator.

    Args:
        min_samples_per_bin: Minimum samples required for reliable calibration
        calibration_update_frequency_days: How often to update calibration

    Returns:
        Configured ConfidenceCalibrator instance
    """
    calibrator = ConfidenceCalibrator(
        min_samples_per_bin=min_samples_per_bin,
        calibration_update_frequency_days=calibration_update_frequency_days
    )
    logger.info("Created new ConfidenceCalibrator")
    return calibrator


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ConfidenceBin",
    "BinStatistics",
    "CalibrationReport",
    "ConfidenceCalibrator",
    "create_confidence_calibrator"
]
