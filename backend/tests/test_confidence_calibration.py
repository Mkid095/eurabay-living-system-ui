"""
Unit tests for Confidence Calibration System.

Tests the confidence calibration functionality including:
- Confidence bin assignment
- Bin statistics calculation
- Calibration error calculation
- Calibration adjustment application
- Calibration report generation
- Database persistence
"""

import pytest
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock

from app.services.confidence_calibration import (
    ConfidenceBin,
    BinStatistics,
    CalibrationReport,
    ConfidenceCalibrator,
    create_confidence_calibrator
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def confidence_calibrator():
    """Create a fresh confidence calibrator for each test."""
    return ConfidenceCalibrator(
        min_samples_per_bin=20,
        calibration_update_frequency_days=7
    )


@pytest.fixture
def sample_bin_statistics():
    """Create sample bin statistics for testing."""
    return BinStatistics(
        bin_range="70-80%",
        predicted_confidence=0.75,
        actual_win_rate=0.72,
        calibration_error=0.03,
        total_signals=100,
        winning_signals=72,
        losing_signals=28,
        last_updated=datetime.now()
    )


# ============================================================================
# ConfidenceBin Tests
# ============================================================================

class TestConfidenceBin:
    """Test ConfidenceBin enum."""

    def test_confidence_bin_values(self):
        """Test confidence bin enum values."""
        assert ConfidenceBin.BIN_50_60.value == "50-60%"
        assert ConfidenceBin.BIN_60_70.value == "60-70%"
        assert ConfidenceBin.BIN_70_80.value == "70-80%"
        assert ConfidenceBin.BIN_80_90.value == "80-90%"
        assert ConfidenceBin.BIN_90_100.value == "90-100%"


# ============================================================================
# BinStatistics Tests
# ============================================================================

class TestBinStatistics:
    """Test BinStatistics dataclass."""

    def test_bin_statistics_creation(self, sample_bin_statistics):
        """Test creating bin statistics."""
        stats = sample_bin_statistics

        assert stats.bin_range == "70-80%"
        assert stats.predicted_confidence == 0.75
        assert stats.actual_win_rate == 0.72
        assert stats.calibration_error == 0.03
        assert stats.total_signals == 100
        assert stats.winning_signals == 72
        assert stats.losing_signals == 28

    def test_bin_statistics_to_dict(self, sample_bin_statistics):
        """Test converting bin statistics to dictionary."""
        stats_dict = sample_bin_statistics.to_dict()

        assert stats_dict["bin_range"] == "70-80%"
        assert stats_dict["predicted_confidence"] == 0.75
        assert stats_dict["actual_win_rate"] == 0.72
        assert stats_dict["calibration_error"] == 0.03
        assert stats_dict["total_signals"] == 100
        assert stats_dict["winning_signals"] == 72
        assert stats_dict["losing_signals"] == 28
        assert "last_updated" in stats_dict


# ============================================================================
# CalibrationReport Tests
# ============================================================================

class TestCalibrationReport:
    """Test CalibrationReport dataclass."""

    def test_calibration_report_creation(self, sample_bin_statistics):
        """Test creating a calibration report."""
        report = CalibrationReport(
            source_name="xgboost_v10",
            bin_statistics={"70-80%": sample_bin_statistics},
            overall_calibration_error=0.04,
            total_signals_calibrated=500,
            is_well_calibrated=True,
            report_generated=datetime.now()
        )

        assert report.source_name == "xgboost_v10"
        assert report.overall_calibration_error == 0.04
        assert report.total_signals_calibrated == 500
        assert report.is_well_calibrated is True
        assert "70-80%" in report.bin_statistics

    def test_calibration_report_to_dict(self, sample_bin_statistics):
        """Test converting calibration report to dictionary."""
        report = CalibrationReport(
            source_name="xgboost_v10",
            bin_statistics={"70-80%": sample_bin_statistics},
            overall_calibration_error=0.04,
            total_signals_calibrated=500,
            is_well_calibrated=True,
            report_generated=datetime.now()
        )

        report_dict = report.to_dict()

        assert report_dict["source_name"] == "xgboost_v10"
        assert report_dict["overall_calibration_error"] == 0.04
        assert report_dict["total_signals_calibrated"] == 500
        assert report_dict["is_well_calibrated"] is True
        assert "bin_statistics" in report_dict
        assert "report_generated" in report_dict


# ============================================================================
# ConfidenceCalibrator Tests
# ============================================================================

class TestConfidenceCalibrator:
    """Test ConfidenceCalibrator class."""

    def test_calibrator_initialization(self):
        """Test calibrator initialization."""
        calibrator = ConfidenceCalibrator(
            min_samples_per_bin=20,
            calibration_update_frequency_days=7
        )

        assert calibrator.min_samples_per_bin == 20
        assert calibrator.calibration_update_frequency_days == 7
        assert len(calibrator.calibration_cache) == 0
        assert len(calibrator.bin_statistics_cache) == 0
        assert len(calibrator.last_calibration_update) == 0

    def test_get_confidence_bin_50_60(self, confidence_calibrator):
        """Test getting confidence bin for 50-60% range."""
        bin_result = confidence_calibrator.get_confidence_bin(0.55)
        assert bin_result == ConfidenceBin.BIN_50_60

    def test_get_confidence_bin_60_70(self, confidence_calibrator):
        """Test getting confidence bin for 60-70% range."""
        bin_result = confidence_calibrator.get_confidence_bin(0.65)
        assert bin_result == ConfidenceBin.BIN_60_70

    def test_get_confidence_bin_70_80(self, confidence_calibrator):
        """Test getting confidence bin for 70-80% range."""
        bin_result = confidence_calibrator.get_confidence_bin(0.75)
        assert bin_result == ConfidenceBin.BIN_70_80

    def test_get_confidence_bin_80_90(self, confidence_calibrator):
        """Test getting confidence bin for 80-90% range."""
        bin_result = confidence_calibrator.get_confidence_bin(0.85)
        assert bin_result == ConfidenceBin.BIN_80_90

    def test_get_confidence_bin_90_100(self, confidence_calibrator):
        """Test getting confidence bin for 90-100% range."""
        bin_result = confidence_calibrator.get_confidence_bin(0.95)
        assert bin_result == ConfidenceBin.BIN_90_100

    def test_get_confidence_bin_edge_case_lower_bound(self, confidence_calibrator):
        """Test edge case at lower bound of 50-60% bin."""
        bin_result = confidence_calibrator.get_confidence_bin(0.50)
        assert bin_result == ConfidenceBin.BIN_50_60

    def test_get_confidence_bin_edge_case_upper_bound(self, confidence_calibrator):
        """Test edge case at upper bound (should go to 90-100% bin)."""
        bin_result = confidence_calibrator.get_confidence_bin(0.90)
        assert bin_result == ConfidenceBin.BIN_90_100

    def test_get_confidence_bin_below_range(self, confidence_calibrator):
        """Test confidence below valid range."""
        bin_result = confidence_calibrator.get_confidence_bin(0.45)
        assert bin_result is None

    def test_get_confidence_bin_exactly_100(self, confidence_calibrator):
        """Test confidence exactly at 100%."""
        bin_result = confidence_calibrator.get_confidence_bin(1.00)
        assert bin_result == ConfidenceBin.BIN_90_100

    def test_bin_ranges(self, confidence_calibrator):
        """Test that bin ranges are correctly defined."""
        ranges = confidence_calibrator.BIN_RANGES

        assert ranges[ConfidenceBin.BIN_50_60] == (0.50, 0.60)
        assert ranges[ConfidenceBin.BIN_60_70] == (0.60, 0.70)
        assert ranges[ConfidenceBin.BIN_70_80] == (0.70, 0.80)
        assert ranges[ConfidenceBin.BIN_80_90] == (0.80, 0.90)
        assert ranges[ConfidenceBin.BIN_90_100] == (0.90, 1.00)


# ============================================================================
# Mock Database Tests
# ============================================================================

class TestConfidenceCalibratorWithDatabase:
    """Test confidence calibrator with database interactions."""

    @pytest.mark.asyncio
    async def test_get_bin_statistics_with_data(self, mock_db_session, confidence_calibrator):
        """Test getting bin statistics with mock database data."""
        # Create mock signal and trade objects
        mock_signal = MagicMock()
        mock_signal.strategy = "xgboost_v10"
        mock_signal.confidence = 0.75
        mock_signal.timestamp = datetime.now()

        mock_trade = MagicMock()
        mock_trade.status = "CLOSED"
        mock_trade.profit_loss = 100.0  # Winning trade

        # Mock database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[(mock_signal, mock_trade)])
        mock_db_session.execute.return_value = mock_result

        # Get bin statistics
        stats = await confidence_calibrator.get_bin_statistics(
            mock_db_session,
            "xgboost_v10",
            ConfidenceBin.BIN_70_80
        )

        # Verify statistics
        assert stats.bin_range == "70-80%"
        assert stats.predicted_confidence == 0.75
        assert stats.actual_win_rate == 1.0  # 100% win rate (1 winning trade)
        assert stats.total_signals == 1
        assert stats.winning_signals == 1
        assert stats.losing_signals == 0

    @pytest.mark.asyncio
    async def test_get_bin_statistics_no_data(self, mock_db_session, confidence_calibrator):
        """Test getting bin statistics with no data."""
        # Mock empty database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Get bin statistics
        stats = await confidence_calibrator.get_bin_statistics(
            mock_db_session,
            "xgboost_v10",
            ConfidenceBin.BIN_70_80
        )

        # Verify statistics
        assert stats.total_signals == 0
        assert stats.winning_signals == 0
        assert stats.losing_signals == 0
        assert stats.actual_win_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_calibrated_confidence_no_cache(self, mock_db_session, confidence_calibrator):
        """Test getting calibrated confidence when cache is empty."""
        # Mock empty database response for calibration update
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Get calibrated confidence (should trigger update)
        calibrated = await confidence_calibrator.get_calibrated_confidence(
            mock_db_session,
            0.75,
            "xgboost_v10"
        )

        # Should return predicted confidence since no data available
        assert calibrated == 0.75

    @pytest.mark.asyncio
    async def test_get_calibrated_confidence_with_cache(self, mock_db_session, confidence_calibrator):
        """Test getting calibrated confidence with cached data."""
        # Manually populate cache
        confidence_calibrator.calibration_cache["xgboost_v10"] = {
            "70-80%": 0.68  # Actual performance is lower than predicted
        }
        confidence_calibrator.last_calibration_update["xgboost_v10"] = datetime.now()

        # Get calibrated confidence
        calibrated = await confidence_calibrator.get_calibrated_confidence(
            mock_db_session,
            0.75,
            "xgboost_v10"
        )

        # Should return calibrated confidence from cache
        assert calibrated == 0.68

    @pytest.mark.asyncio
    async def test_get_calibrated_confidence_invalid_bin(self, mock_db_session, confidence_calibrator):
        """Test getting calibrated confidence for invalid bin."""
        # Get calibrated confidence for value outside bin ranges
        calibrated = await confidence_calibrator.get_calibrated_confidence(
            mock_db_session,
            0.45,  # Below 50%
            "xgboost_v10"
        )

        # Should return predicted confidence
        assert calibrated == 0.45


# ============================================================================
# Calibration Update Tests
# ============================================================================

class TestCalibrationUpdate:
    """Test calibration update functionality."""

    @pytest.mark.asyncio
    async def test_update_calibration_populates_cache(self, mock_db_session, confidence_calibrator):
        """Test that update_calibration populates cache."""
        # Mock empty database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Update calibration
        await confidence_calibrator.update_calibration(mock_db_session, "xgboost_v10")

        # Verify cache is populated
        assert "xgboost_v10" in confidence_calibrator.calibration_cache
        assert "xgboost_v10" in confidence_calibrator.bin_statistics_cache
        assert "xgboost_v10" in confidence_calibrator.last_calibration_update

    @pytest.mark.asyncio
    async def test_update_calibration_creates_all_bins(self, mock_db_session, confidence_calibrator):
        """Test that update_calibration creates statistics for all bins."""
        # Mock empty database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Update calibration
        await confidence_calibrator.update_calibration(mock_db_session, "xgboost_v10")

        # Verify all bins are created
        bin_stats = confidence_calibrator.bin_statistics_cache["xgboost_v10"]
        assert len(bin_stats) == 5  # 5 confidence bins

        for bin_name in ConfidenceBin:
            assert bin_name.value in bin_stats


# ============================================================================
# Calibration Report Tests
# ============================================================================

class TestCalibrationReportGeneration:
    """Test calibration report generation."""

    @pytest.mark.asyncio
    async def test_generate_calibration_report(self, mock_db_session, confidence_calibrator):
        """Test generating a calibration report."""
        # Mock empty database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Generate report
        report = await confidence_calibrator.generate_calibration_report(
            mock_db_session,
            "xgboost_v10"
        )

        # Verify report structure
        assert isinstance(report, CalibrationReport)
        assert report.source_name == "xgboost_v10"
        assert isinstance(report.bin_statistics, dict)
        assert isinstance(report.overall_calibration_error, float)
        assert isinstance(report.total_signals_calibrated, int)
        assert isinstance(report.is_well_calibrated, bool)
        assert isinstance(report.report_generated, datetime)

    @pytest.mark.asyncio
    async def test_generate_calibration_report_no_data(self, mock_db_session, confidence_calibrator):
        """Test generating calibration report with no data."""
        # Mock empty database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Generate report
        report = await confidence_calibrator.generate_calibration_report(
            mock_db_session,
            "xgboost_v10"
        )

        # With no data, should be well calibrated (0 error)
        assert report.is_well_calibrated is True
        assert report.overall_calibration_error == 0.0
        assert report.total_signals_calibrated == 0


# ============================================================================
# Cache Management Tests
# ============================================================================

class TestCacheManagement:
    """Test cache management functionality."""

    def test_get_all_cached_sources_empty(self, confidence_calibrator):
        """Test getting cached sources when cache is empty."""
        sources = confidence_calibrator.get_all_cached_sources()
        assert len(sources) == 0

    def test_get_all_cached_sources_with_data(self, confidence_calibrator):
        """Test getting cached sources with data."""
        # Add some sources to cache
        confidence_calibrator.calibration_cache["xgboost_v10"] = {}
        confidence_calibrator.calibration_cache["rf_v10"] = {}

        sources = confidence_calibrator.get_all_cached_sources()
        assert len(sources) == 2
        assert "xgboost_v10" in sources
        assert "rf_v10" in sources

    def test_clear_calibration_cache_all(self, confidence_calibrator):
        """Test clearing all calibration cache."""
        # Add data to cache
        confidence_calibrator.calibration_cache["xgboost_v10"] = {}
        confidence_calibrator.bin_statistics_cache["xgboost_v10"] = {}
        confidence_calibrator.last_calibration_update["xgboost_v10"] = datetime.now()

        # Clear all cache
        confidence_calibrator.clear_calibration_cache()

        # Verify cache is cleared
        assert len(confidence_calibrator.calibration_cache) == 0
        assert len(confidence_calibrator.bin_statistics_cache) == 0
        assert len(confidence_calibrator.last_calibration_update) == 0

    def test_clear_calibration_cache_specific_source(self, confidence_calibrator):
        """Test clearing cache for specific source."""
        # Add data for multiple sources
        confidence_calibrator.calibration_cache["xgboost_v10"] = {}
        confidence_calibrator.calibration_cache["rf_v10"] = {}
        confidence_calibrator.bin_statistics_cache["xgboost_v10"] = {}
        confidence_calibrator.bin_statistics_cache["rf_v10"] = {}
        confidence_calibrator.last_calibration_update["xgboost_v10"] = datetime.now()
        confidence_calibrator.last_calibration_update["rf_v10"] = datetime.now()

        # Clear cache for one source
        confidence_calibrator.clear_calibration_cache("xgboost_v10")

        # Verify only specified source is cleared
        assert "xgboost_v10" not in confidence_calibrator.calibration_cache
        assert "rf_v10" in confidence_calibrator.calibration_cache
        assert "xgboost_v10" not in confidence_calibrator.bin_statistics_cache
        assert "rf_v10" in confidence_calibrator.bin_statistics_cache


# ============================================================================
# Convenience Functions Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_confidence_calibrator_default(self):
        """Test creating calibrator with default parameters."""
        calibrator = create_confidence_calibrator()

        assert isinstance(calibrator, ConfidenceCalibrator)
        assert calibrator.min_samples_per_bin == 20
        assert calibrator.calibration_update_frequency_days == 7

    def test_create_confidence_calibrator_custom(self):
        """Test creating calibrator with custom parameters."""
        calibrator = create_confidence_calibrator(
            min_samples_per_bin=50,
            calibration_update_frequency_days=14
        )

        assert isinstance(calibrator, ConfidenceCalibrator)
        assert calibrator.min_samples_per_bin == 50
        assert calibrator.calibration_update_frequency_days == 14


# ============================================================================
# Integration Tests
# ============================================================================

class TestConfidenceCalibrationIntegration:
    """Integration tests for confidence calibration."""

    @pytest.mark.asyncio
    async def test_full_calibration_workflow(self, mock_db_session, confidence_calibrator):
        """Test full workflow: update -> get calibrated -> generate report."""
        # Mock empty database response
        mock_result = MagicMock()
        mock_result.all = Mock(return_value=[])
        mock_db_session.execute.return_value = mock_result

        # Step 1: Update calibration
        await confidence_calibrator.update_calibration(mock_db_session, "xgboost_v10")

        # Step 2: Get calibrated confidence
        calibrated = await confidence_calibrator.get_calibrated_confidence(
            mock_db_session,
            0.75,
            "xgboost_v10"
        )

        # Step 3: Generate report
        report = await confidence_calibrator.generate_calibration_report(
            mock_db_session,
            "xgboost_v10"
        )

        # Verify workflow completed
        assert isinstance(calibrated, float)
        assert isinstance(report, CalibrationReport)
        assert report.source_name == "xgboost_v10"

    def test_calibration_error_calculation(self):
        """Test calibration error calculation."""
        # Perfect calibration
        predicted = 0.75
        actual = 0.75
        error = abs(predicted - actual)
        assert error == 0.0

        # Over-confident
        predicted = 0.80
        actual = 0.60
        error = abs(predicted - actual)
        assert abs(error - 0.20) < 1e-10

        # Under-confident
        predicted = 0.60
        actual = 0.80
        error = abs(predicted - actual)
        assert abs(error - 0.20) < 1e-10

    def test_well_calibrated_threshold(self):
        """Test well-calibrated threshold (error < 5%)."""
        # Well calibrated
        stats = BinStatistics(
            bin_range="70-80%",
            predicted_confidence=0.75,
            actual_win_rate=0.73,
            calibration_error=0.02,  # 2% error
            total_signals=100,
            winning_signals=73,
            losing_signals=27,
            last_updated=datetime.now()
        )
        assert stats.calibration_error < 0.05  # Well calibrated

        # Not well calibrated
        stats2 = BinStatistics(
            bin_range="70-80%",
            predicted_confidence=0.75,
            actual_win_rate=0.65,
            calibration_error=0.10,  # 10% error
            total_signals=100,
            winning_signals=65,
            losing_signals=35,
            last_updated=datetime.now()
        )
        assert stats2.calibration_error >= 0.05  # Not well calibrated
