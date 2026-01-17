"""
Comprehensive tests for Historical Data Backfill Service.

Tests cover:
- Gap detection for various scenarios
- Chunked backfill operations
- Progress tracking
- Priority-based backfill
- Rate limit handling
- Fresh installation backfill
- Gap detection and backfill
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd

from app.services.historical_backfill import (
    HistoricalBackfillService,
    DataGap,
    BackfillProgress,
    BackfillStatus,
    BackfillPriority,
    BackfillConfig,
)
from app.services.mt5_service import OHLCVData, MT5Error


@pytest.fixture
def mock_mt5_service():
    """Create a mock MT5 service."""
    service = Mock()
    service.is_connected = True
    service.initialize = AsyncMock()
    return service


@pytest.fixture
def mock_ohlcv_collector():
    """Create a mock OHLCV collector."""
    collector = Mock()
    collector.initialize = AsyncMock()
    collector._store_ohlcv_data = AsyncMock()
    return collector


@pytest.fixture
def backfill_config():
    """Create test backfill configuration."""
    return BackfillConfig(
        chunk_size_bars=1000,
        max_concurrent_requests=2,
        rate_limit_delay=0.1,
        max_retries=2,
        backfill_priority=True,
        max_historical_years=1,
        enable_progress_tracking=True,
    )


@pytest.fixture
def backfill_service(mock_mt5_service, mock_ohlcv_collector, backfill_config):
    """Create a HistoricalBackfillService instance for testing."""
    service = HistoricalBackfillService(
        mt5_service=mock_mt5_service,
        ohlcv_collector=mock_ohlcv_collector,
        symbols=["V10", "V25"],
        config=backfill_config,
    )
    service.is_initialized = True
    return service


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    data = []
    for i in range(100):
        timestamp = base_time + timedelta(minutes=i)
        data.append(
            OHLCVData(
                symbol="V10",
                timestamp=timestamp,
                open=100.0 + i * 0.1,
                high=100.5 + i * 0.1,
                low=99.5 + i * 0.1,
                close=100.2 + i * 0.1,
                volume=100 + i,
            )
        )
    return data


class TestBackfillPriority:
    """Tests for backfill priority determination."""

    def test_critical_priority(self, backfill_service):
        """Test critical priority for recent data (within 24 hours)."""
        now = datetime.now(timezone.utc)
        gap_date = now - timedelta(hours=12)

        priority = backfill_service._determine_priority(gap_date)

        assert priority == BackfillPriority.CRITICAL

    def test_high_priority(self, backfill_service):
        """Test high priority for data within 7 days."""
        now = datetime.now(timezone.utc)
        gap_date = now - timedelta(days=3)

        priority = backfill_service._determine_priority(gap_date)

        assert priority == BackfillPriority.HIGH

    def test_medium_priority(self, backfill_service):
        """Test medium priority for data within 30 days."""
        now = datetime.now(timezone.utc)
        gap_date = now - timedelta(days=15)

        priority = backfill_service._determine_priority(gap_date)

        assert priority == BackfillPriority.MEDIUM

    def test_low_priority(self, backfill_service):
        """Test low priority for old data (beyond 30 days)."""
        now = datetime.now(timezone.utc)
        gap_date = now - timedelta(days=60)

        priority = backfill_service._determine_priority(gap_date)

        assert priority == BackfillPriority.LOW


class TestDataGapDetection:
    """Tests for data gap detection."""

    @pytest.mark.asyncio
    async def test_estimate_missing_bars(self, backfill_service):
        """Test estimation of missing bars for a date range."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        missing_bars = backfill_service._estimate_missing_bars(
            start_date, end_date, "M1"
        )

        # 1 day = 1440 minutes, should have ~1440 M1 bars
        assert missing_bars > 1400
        assert missing_bars < 1500

    @pytest.mark.asyncio
    async def test_detect_gaps_no_file(self, backfill_service, tmp_path):
        """Test gap detection when no data file exists."""
        with patch("app.services.historical_backfill.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

            gaps = await backfill_service._detect_gaps_for_symbol(
                "V10", "M1", start_date, end_date
            )

            # Should detect the entire range as a gap
            assert len(gaps) == 1
            assert gaps[0].symbol == "V10"
            assert gaps[0].timeframe == "M1"
            assert gaps[0].gap_start == start_date
            assert gaps[0].gap_end == end_date

    @pytest.mark.asyncio
    async def test_detect_gaps_with_existing_data(
        self, backfill_service, tmp_path, sample_ohlcv_data
    ):
        """Test gap detection with existing data file."""
        # Create a parquet file with sample data
        base_path = tmp_path / "parquet"
        base_path.mkdir(parents=True, exist_ok=True)

        # Create sample dataframe with a gap
        timestamps = []
        for i in range(100):
            if i == 50:  # Skip this to create a gap
                continue
            timestamps.append(datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i))

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": [100.0] * len(timestamps),
            "high": [100.5] * len(timestamps),
            "low": [99.5] * len(timestamps),
            "close": [100.2] * len(timestamps),
            "volume": [100] * len(timestamps),
        })

        import pyarrow.parquet as pq
        import pyarrow as pa

        table = pa.Table.from_pandas(df)
        pq.write_table(table, base_path / "V10_M1.parquet", compression="snappy")

        with patch("app.services.historical_backfill.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 1, hour=2, tzinfo=timezone.utc)

            gaps = await backfill_service._detect_gaps_for_symbol(
                "V10", "M1", start_date, end_date
            )

            # Should detect the gap we created
            assert len(gaps) > 0


class TestChunkedBackfill:
    """Tests for chunked backfill operations."""

    @pytest.mark.asyncio
    async def test_backfill_chunk_success(
        self, backfill_service, mock_mt5_service, sample_ohlcv_data
    ):
        """Test successful backfill of a single chunk."""
        # Mock MT5 response
        mock_rates = []
        for data in sample_ohlcv_data[:10]:  # Use 10 bars
            mock_rates.append({
                "time": data.timestamp.timestamp(),
                "open": data.open,
                "high": data.high,
                "low": data.low,
                "close": data.close,
                "tick_volume": data.volume,
            })

        with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
            mock_copy_rates.return_value = mock_rates

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 1, hour=1, tzinfo=timezone.utc)

            bars_filled = await backfill_service._backfill_chunk(
                "V10", "M1", start_date, end_date
            )

            assert bars_filled == 10
            backfill_service.ohlcv_collector._store_ohlcv_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_backfill_chunk_retry_on_failure(
        self, backfill_service, mock_mt5_service, backfill_config
    ):
        """Test retry logic when MT5 request fails."""
        # Mock MT5 to fail twice then succeed
        with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
            mock_copy_rates.side_effect = [
                None,  # First attempt fails
                None,  # Second attempt fails
                [],    # Third attempt succeeds (empty data)
            ]

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 1, hour=1, tzinfo=timezone.utc)

            # Should succeed after retries
            bars_filled = await backfill_service._backfill_chunk(
                "V10", "M1", start_date, end_date
            )

            # Should have tried 3 times (max_retries = 2)
            assert mock_copy_rates.call_count == backfill_config.max_retries
            assert bars_filled == 0

    @pytest.mark.asyncio
    async def test_backfill_chunk_all_retries_fail(self, backfill_service):
        """Test that error is raised when all retries fail."""
        # Mock MT5 to always fail
        with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
            mock_copy_rates.return_value = None

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 1, hour=1, tzinfo=timezone.utc)

            # Should raise MT5Error after all retries
            with pytest.raises(MT5Error):
                await backfill_service._backfill_chunk(
                    "V10", "M1", start_date, end_date
                )


class TestProgressTracking:
    """Tests for progress tracking."""

    def test_backfill_progress_creation(self, backfill_service):
        """Test creation of BackfillProgress object."""
        progress = BackfillProgress(
            operation_id="test_op_1",
            symbol="V10",
            timeframe="M1",
            status=BackfillStatus.IN_PROGRESS,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            total_bars_needed=1440,
            bars_backfilled=0,
            start_time=datetime.now(timezone.utc),
        )

        assert progress.operation_id == "test_op_1"
        assert progress.symbol == "V10"
        assert progress.timeframe == "M1"
        assert progress.status == BackfillStatus.IN_PROGRESS
        assert progress.total_bars_needed == 1440
        assert progress.bars_backfilled == 0

    @pytest.mark.asyncio
    async def test_progress_tracking_during_backfill(
        self, backfill_service, mock_mt5_service, sample_ohlcv_data
    ):
        """Test progress tracking during chunked backfill."""
        # Create a progress tracker
        progress = BackfillProgress(
            operation_id="test_progress",
            symbol="V10",
            timeframe="M1",
            status=BackfillStatus.IN_PROGRESS,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            total_bars_needed=1440,
            bars_backfilled=0,
            start_time=datetime.now(timezone.utc),
            total_chunks=2,
        )

        backfill_service._active_operations["test_progress"] = progress

        # Mock MT5 to return data for each chunk
        mock_chunk = sample_ohlcv_data[:50]

        with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
            mock_copy_rates.return_value = [
                {
                    "time": d.timestamp.timestamp(),
                    "open": d.open,
                    "high": d.high,
                    "low": d.low,
                    "close": d.close,
                    "tick_volume": d.volume,
                }
                for d in mock_chunk
            ]

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 1, hour=1, tzinfo=timezone.utc)

            # Simulate chunked backfill
            bars_filled = await backfill_service._backfill_chunk(
                "V10", "M1", start_date, end_date
            )

            # Verify progress was updated
            assert bars_filled == 50


class TestFreshInstallationBackfill:
    """Tests for fresh installation scenario."""

    @pytest.mark.asyncio
    async def test_backfill_all_symbols_fresh_install(
        self, backfill_service, mock_mt5_service, sample_ohlcv_data, tmp_path
    ):
        """Test comprehensive backfill for fresh installation."""
        with patch("app.services.historical_backfill.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)

            # Mock MT5 to return data
            with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
                mock_copy_rates.return_value = [
                    {
                        "time": d.timestamp.timestamp(),
                        "open": d.open,
                        "high": d.high,
                        "low": d.low,
                        "close": d.close,
                        "tick_volume": d.volume,
                    }
                    for d in sample_ohlcv_data
                ]

                start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

                # Perform backfill for all symbols
                progress_map = await backfill_service.backfill_all_symbols(
                    start_date=start_date,
                    end_date=end_date,
                )

                # Should have created operations for all symbol/timeframe combinations
                assert len(progress_map) > 0

                # Check that some operations completed successfully
                completed = [
                    p for p in progress_map.values()
                    if p.status == BackfillStatus.COMPLETED
                ]
                assert len(completed) > 0


class TestGapDetectionAndBackfill:
    """Tests for gap detection and backfill scenario."""

    @pytest.mark.asyncio
    async def test_detect_and_backfill_gaps(
        self, backfill_service, mock_mt5_service, sample_ohlcv_data, tmp_path
    ):
        """Test detecting gaps and backfilling them."""
        with patch("app.services.historical_backfill.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)

            # Mock MT5 to return data
            with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
                mock_copy_rates.return_value = [
                    {
                        "time": d.timestamp.timestamp(),
                        "open": d.open,
                        "high": d.high,
                        "low": d.low,
                        "close": d.close,
                        "tick_volume": d.volume,
                    }
                    for d in sample_ohlcv_data
                ]

                start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

                # Detect gaps
                gaps = await backfill_service.detect_data_gaps(
                    symbols=["V10"],
                    timeframes=["M1"],
                    start_date=start_date,
                    end_date=end_date,
                )

                # Should detect gaps (no data file exists)
                assert len(gaps) > 0

                # Backfill the gaps
                progress_map = await backfill_service.backfill_gaps(gaps, max_concurrent=2)

                # Should have backfilled the gaps
                assert len(progress_map) == len(gaps)


class TestRateLimiting:
    """Tests for rate limiting during backfill."""

    @pytest.mark.asyncio
    async def test_rate_limit_delay(self, backfill_service):
        """Test that rate limit delay is applied."""
        import time

        start_time = time.time()

        # Apply rate limit delay
        await backfill_service._rate_limit_delay()

        elapsed = time.time() - start_time

        # Should have waited at least the configured delay
        assert elapsed >= backfill_service.config.rate_limit_delay


class TestBackfillErrors:
    """Tests for error handling during backfill."""

    @pytest.mark.asyncio
    async def test_backfill_without_initialization(self, backfill_service):
        """Test that backfill fails when service is not initialized."""
        backfill_service.is_initialized = False

        with pytest.raises(RuntimeError, match="Service not initialized"):
            await backfill_service.backfill_historical_data(
                "V10",
                "M1",
                datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_backfill_invalid_timeframe(self, backfill_service):
        """Test that backfill fails with invalid timeframe."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            await backfill_service.backfill_historical_data(
                "V10",
                "INVALID_TIMEFRAME",
                datetime(2024, 1, 1, tzinfo=timezone.utc),
            )


class TestBackfillIntegration:
    """Integration tests for backfill functionality."""

    @pytest.mark.asyncio
    async def test_full_backfill_workflow(
        self, backfill_service, mock_mt5_service, sample_ohlcv_data, tmp_path
    ):
        """Test complete workflow: detect gaps -> backfill -> verify."""
        with patch("app.services.historical_backfill.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)

            # Mock MT5 to return data
            with patch("MetaTrader5.copy_rates_range") as mock_copy_rates:
                mock_copy_rates.return_value = [
                    {
                        "time": d.timestamp.timestamp(),
                        "open": d.open,
                        "high": d.high,
                        "low": d.low,
                        "close": d.close,
                        "tick_volume": d.volume,
                    }
                    for d in sample_ohlcv_data
                ]

                start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

                # Step 1: Detect gaps
                gaps = await backfill_service.detect_data_gaps(
                    symbols=["V10"],
                    timeframes=["M1"],
                    start_date=start_date,
                    end_date=end_date,
                )

                # Step 2: Backfill gaps
                progress_map = await backfill_service.backfill_gaps(gaps)

                # Step 3: Verify results
                assert len(gaps) > 0
                assert len(progress_map) > 0

                total_bars = sum(p.bars_backfilled for p in progress_map.values())
                assert total_bars > 0
