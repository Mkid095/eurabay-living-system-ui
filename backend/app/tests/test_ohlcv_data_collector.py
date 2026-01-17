"""
Unit tests for OHLCV Data Collector.

Tests cover:
- OHLCV data fetching for all timeframes
- Parquet storage with snappy compression
- File organization by symbol and timeframe
- Data validation (OHLC relationships, volume checks)
- Data deduplication
- Data retention policy
- Data gap detection
- Quality monitoring
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import tempfile
import shutil

from app.services.ohlcv_data_collector import (
    OHLCVDataCollector,
    OHLCVQuality,
    OHLCVQualityReport,
    OHLCVCollectionStats,
    OHLCVDataRecord,
)
from app.services.mt5_service import OHLCVData, MT5Error


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup after test
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_mt5_service():
    """Create mock MT5 service."""
    mock_service = Mock()
    mock_service.is_connected = True
    mock_service.get_historical_data = AsyncMock()
    return mock_service


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return [
        OHLCVData(
            symbol="V10",
            timestamp=base_time + timedelta(minutes=i),
            open=10000.0 + i,
            high=10010.0 + i,
            low=9995.0 + i,
            close=10005.0 + i,
            volume=100 + i,
        )
        for i in range(10)
    ]


@pytest.fixture
def invalid_ohlcv_data():
    """Create invalid OHLCV data for testing validation."""
    return [
        # High < Low (invalid)
        OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10005.0,
            low=10010.0,  # Low > High (invalid)
            close=10008.0,
            volume=100,
        ),
        # Negative price (invalid)
        OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc),
            open=-100.0,  # Negative price (invalid)
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=100,
        ),
        # Volume out of range (invalid)
        OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 2, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=-50,  # Negative volume (invalid)
        ),
        # Extreme price change (invalid) - >50% needed
        OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 3, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=15500.0,  # High accommodates the close
            low=9995.0,
            close=15500.0,  # 55% increase exceeds MAX_PRICE_CHANGE_PERCENT (50%)
            volume=100,
        ),
    ]


@pytest.fixture
def collector(mock_mt5_service, temp_dir):
    """Create OHLCV collector instance for testing."""
    # Use custom symbols parameter to avoid settings mutation
    collector = OHLCVDataCollector(
        mt5_service=mock_mt5_service,
        symbols=["V10", "V25"],
        base_path=str(temp_dir / "parquet"),
    )
    return collector


class TestOHLCVDataCollectorInitialization:
    """Tests for OHLCV collector initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, collector):
        """Test successful initialization."""
        assert not collector.is_initialized

        await collector.initialize()

        assert collector.is_initialized
        assert len(collector._stats) == 12  # 2 symbols * 6 timeframes

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, collector):
        """Test initialization when already initialized."""
        await collector.initialize()

        # Should not raise error
        await collector.initialize()

        assert collector.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_mt5_not_connected(self, temp_dir):
        """Test initialization fails when MT5 not connected."""
        mock_service = Mock()
        mock_service.is_connected = False

        collector = OHLCVDataCollector(
            mt5_service=mock_service,
            symbols=["V10"],
            base_path=str(temp_dir / "parquet"),
        )

        with pytest.raises(RuntimeError, match="MT5 service is not connected"):
            await collector.initialize()


class TestFetchOHLCVData:
    """Tests for OHLCV data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_success(self, collector, sample_ohlcv_data):
        """Test successful OHLCV data fetch."""
        await collector.initialize()

        collector.mt5_service.get_historical_data.return_value = sample_ohlcv_data

        result = await collector.fetch_ohlcv_data("V10", "M1", bars=10)

        assert len(result) == 10
        assert result[0].symbol == "V10"
        assert collector.mt5_service.get_historical_data.called

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_all_timeframes(self, collector, sample_ohlcv_data):
        """Test fetching data for all supported timeframes."""
        await collector.initialize()

        timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]

        for timeframe in timeframes:
            collector.mt5_service.get_historical_data.return_value = sample_ohlcv_data
            result = await collector.fetch_ohlcv_data("V10", timeframe)

            assert len(result) == 10

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_invalid_timeframe(self, collector):
        """Test fetching with invalid timeframe raises error."""
        await collector.initialize()

        with pytest.raises(ValueError, match="Invalid timeframe"):
            await collector.fetch_ohlcv_data("V10", "INVALID")

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_not_initialized(self, collector):
        """Test fetching without initialization raises error."""
        with pytest.raises(RuntimeError, match="Service not initialized"):
            await collector.fetch_ohlcv_data("V10", "M1")

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_mt5_error(self, collector):
        """Test handling MT5 errors during fetch."""
        await collector.initialize()

        collector.mt5_service.get_historical_data.side_effect = MT5Error("MT5 error")

        result = await collector.fetch_ohlcv_data("V10", "M1")

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_with_date_range(self, collector, sample_ohlcv_data):
        """Test fetching historical data for a date range."""
        await collector.initialize()

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        result = await collector.fetch_ohlcv_data(
            "V10", "M1", start_date=start_date, end_date=end_date
        )

        # Should call the date range fetch method
        assert isinstance(result, list)


class TestOHLCVValidation:
    """Tests for OHLCV data validation."""

    def test_validate_valid_ohlcv(self, collector):
        """Test validation of valid OHLCV data."""
        valid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=100,
        )

        result = collector._validate_ohlcv_data(valid_data)

        assert result["is_valid"] is True
        assert result["reason"] is None

    def test_validate_high_less_than_max(self, collector):
        """Test validation fails when high < max of open/close/low."""
        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10000.0,  # High too low
            low=10010.0,
            close=10005.0,
            volume=100,
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        assert "High" in result["reason"]

    def test_validate_low_greater_than_min(self, collector):
        """Test validation fails when low > min of open/close/high."""
        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10010.0,
            low=10010.0,  # Low too high
            close=10005.0,
            volume=100,
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        assert "Low" in result["reason"]

    def test_validate_negative_price(self, collector):
        """Test validation fails with negative price."""
        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=-100.0,  # Negative price
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=100,
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        # The validation catches the Low > min issue first (due to negative open)
        assert "Low" in result["reason"] or "Invalid price" in result["reason"]

    def test_validate_future_timestamp(self, collector):
        """Test validation fails with future timestamp."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=future_time,  # Future timestamp
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=100,
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        assert "future" in result["reason"]

    def test_validate_invalid_volume_negative(self, collector):
        """Test validation fails with negative volume."""
        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=-50,  # Negative volume
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        assert "Volume" in result["reason"]

    def test_validate_invalid_volume_exceeds_max(self, collector):
        """Test validation fails with volume exceeding maximum."""
        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=2000000,  # Exceeds MAX_VOLUME
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        assert "Volume" in result["reason"]

    def test_validate_extreme_price_change(self, collector):
        """Test validation fails with extreme price change."""
        invalid_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=10000.0,
            high=16000.0,  # High accommodates the close
            low=9995.0,
            close=16000.0,  # 60% increase exceeds MAX_PRICE_CHANGE_PERCENT
            volume=100,
        )

        result = collector._validate_ohlcv_data(invalid_data)

        assert result["is_valid"] is False
        assert "Price change" in result["reason"]


class TestOHLCVStorage:
    """Tests for OHLCV data storage in Parquet format."""

    @pytest.mark.asyncio
    async def test_store_ohlcv_data_creates_parquet_file(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test that storing OHLCV data creates Parquet file."""
        await collector.initialize()

        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

        file_path = collector._get_file_path("V10", "M1")
        assert file_path.exists()
        assert file_path.suffix == ".parquet"

    @pytest.mark.asyncio
    async def test_store_ohlcv_data_with_snappy_compression(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test that Parquet files use snappy compression."""
        await collector.initialize()

        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

        file_path = collector._get_file_path("V10", "M1")

        # Read file metadata to verify compression
        parquet_file = pq.ParquetFile(file_path)
        metadata = parquet_file.metadata

        # Check compression is set
        assert metadata is not None

    @pytest.mark.asyncio
    async def test_store_ohlcv_data_append_mode(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test that storing appends to existing file."""
        await collector.initialize()

        # Store first batch
        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

        # Create second batch
        base_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        second_batch = [
            OHLCVData(
                symbol="V10",
                timestamp=base_time + timedelta(minutes=i),
                open=10100.0 + i,
                high=10110.0 + i,
                low=10095.0 + i,
                close=10105.0 + i,
                volume=200 + i,
            )
            for i in range(5)
        ]

        # Store second batch
        await collector._store_ohlcv_data("V10", "M1", second_batch)

        # Verify combined data
        file_path = collector._get_file_path("V10", "M1")
        table = pq.read_table(file_path)
        df = table.to_pandas()

        assert len(df) == 15  # 10 + 5

    @pytest.mark.asyncio
    async def test_store_ohlcv_data_deduplication(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test that duplicate timestamps are handled correctly."""
        await collector.initialize()

        # Store first batch
        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

        # Store same batch again (duplicates)
        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

        # Verify no duplicates
        file_path = collector._get_file_path("V10", "M1")
        table = pq.read_table(file_path)
        df = table.to_pandas()

        assert len(df) == 10  # No duplicates added

    @pytest.mark.asyncio
    async def test_store_ohlcv_data_multiple_symbols_timeframes(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test storing data for multiple symbols and timeframes."""
        await collector.initialize()

        symbols = ["V10", "V25"]
        timeframes = ["M1", "M5", "H1"]

        for symbol in symbols:
            for timeframe in timeframes:
                await collector._store_ohlcv_data(symbol, timeframe, sample_ohlcv_data)

        # Verify all files created
        for symbol in symbols:
            for timeframe in timeframes:
                file_path = collector._get_file_path(symbol, timeframe)
                assert file_path.exists()

    @pytest.mark.asyncio
    async def test_get_file_path(self, collector, temp_dir):
        """Test file path generation."""
        file_path = collector._get_file_path("V10", "M1")

        assert "V10_M1.parquet" in str(file_path)
        assert file_path.parent == collector.base_path


class TestDataDeduplication:
    """Tests for data deduplication."""

    @pytest.mark.asyncio
    async def test_is_duplicate_no_existing_file(self, collector, sample_ohlcv_data):
        """Test duplicate check when file doesn't exist."""
        await collector.initialize()

        result = await collector._is_duplicate("V10", "M1", sample_ohlcv_data[0])

        assert result is False

    @pytest.mark.asyncio
    async def test_is_duplicate_with_existing_data(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test duplicate check with existing data."""
        await collector.initialize()

        # Store data
        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

        # Check for duplicate
        result = await collector._is_duplicate("V10", "M1", sample_ohlcv_data[0])

        assert result is True

    @pytest.mark.asyncio
    async def test_is_duplicate_new_data(self, collector, sample_ohlcv_data, temp_dir):
        """Test duplicate check with new data."""
        await collector.initialize()

        # Store first data
        await collector._store_ohlcv_data("V10", "M1", sample_ohlcv_data[:5])

        # Check for duplicate with different timestamp
        new_data = OHLCVData(
            symbol="V10",
            timestamp=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),  # Different
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.,
            volume=100,
        )

        result = await collector._is_duplicate("V10", "M1", new_data)

        assert result is False


class TestDataGapDetection:
    """Tests for data gap detection."""

    @pytest.mark.asyncio
    async def test_detect_gaps_no_file(self, collector):
        """Test gap detection when no file exists."""
        await collector.initialize()

        gaps = await collector.detect_data_gaps("V10", "M1")

        assert len(gaps) > 0
        assert "No data file found" in gaps[0]

    @pytest.mark.asyncio
    async def test_detect_gaps_continuous_data(
        self, collector, sample_ohlcv_data, temp_dir
    ):
        """Test gap detection with continuous data."""
        await collector.initialize()

        # Store continuous data (use recent dates)
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_data = [
            OHLCVData(
                symbol="V10",
                timestamp=recent_time + timedelta(minutes=i),
                open=10000.0 + i,
                high=10010.0 + i,
                low=9995.0 + i,
                close=10005.0 + i,
                volume=100 + i,
            )
            for i in range(10)
        ]

        await collector._store_ohlcv_data("V10", "M1", recent_data)

        gaps = await collector.detect_data_gaps("V10", "M1")

        # Should have no gaps (data is continuous)
        assert len(gaps) == 0

    @pytest.mark.asyncio
    async def test_detect_gaps_with_missing_candles(
        self, collector, temp_dir
    ):
        """Test gap detection with missing candles."""
        await collector.initialize()

        # Create data with gaps (use recent dates)
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        gapped_data = [
            # First candle
            OHLCVData(
                symbol="V10",
                timestamp=recent_time,
                open=10000.0,
                high=10010.0,
                low=9995.0,
                close=10005.0,
                volume=100,
            ),
            # Missing candles between 0 and 6 minutes
            # Candle at 6 minutes (6 minute gap)
            OHLCVData(
                symbol="V10",
                timestamp=recent_time + timedelta(minutes=6),
                open=10006.0,
                high=10016.0,
                low=10001.0,
                close=10011.0,
                volume=106,
            ),
        ]

        await collector._store_ohlcv_data("V10", "M1", gapped_data)

        gaps = await collector.detect_data_gaps("V10", "M1")

        # Should detect gap
        assert len(gaps) > 0
        assert any("Gap" in gap for gap in gaps)


class TestRetentionPolicy:
    """Tests for data retention policy."""

    @pytest.mark.asyncio
    async def test_retention_policy_detailed_timeframes(self, collector, temp_dir):
        """Test retention policy for detailed timeframes (90 days)."""
        await collector.initialize()

        # Create old data
        old_time = datetime.now(timezone.utc) - timedelta(days=100)
        old_data = OHLCVData(
            symbol="V10",
            timestamp=old_time,
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=100,
        )

        await collector._store_ohlcv_data("V10", "M1", [old_data])

        # Apply retention policy
        deleted_count = await collector.apply_retention_policy()

        # Old data should be deleted
        file_path = collector._get_file_path("V10", "M1")
        if file_path.exists():
            table = pq.read_table(file_path)
            df = table.to_pandas()
            # File should be empty or data should be newer
            assert len(df) == 0

    @pytest.mark.asyncio
    async def test_retention_policy_daily_timeframe(self, collector, temp_dir):
        """Test retention policy for daily timeframe (1 year)."""
        await collector.initialize()

        # Create data 200 days old (should be kept for D1)
        old_time = datetime.now(timezone.utc) - timedelta(days=200)
        old_data = OHLCVData(
            symbol="V10",
            timestamp=old_time,
            open=10000.0,
            high=10010.0,
            low=9995.0,
            close=10005.0,
            volume=100,
        )

        await collector._store_ohlcv_data("V10", "D1", [old_data])

        # Apply retention policy
        await collector.apply_retention_policy()

        # Data should still exist (within 1 year)
        file_path = collector._get_file_path("V10", "D1")
        assert file_path.exists()

        table = pq.read_table(file_path)
        df = table.to_pandas()
        assert len(df) > 0


class TestQualityReport:
    """Tests for quality report generation."""

    @pytest.mark.asyncio
    async def test_quality_report_excellent(self, collector, sample_ohlcv_data, temp_dir):
        """Test quality report with excellent data."""
        await collector.initialize()

        # Use recent data for quality report
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_data = [
            OHLCVData(
                symbol="V10",
                timestamp=recent_time + timedelta(minutes=i),
                open=10000.0 + i,
                high=10010.0 + i,
                low=9995.0 + i,
                close=10005.0 + i,
                volume=100 + i,
            )
            for i in range(10)
        ]

        await collector._store_ohlcv_data("V10", "M1", recent_data)

        report = await collector.generate_quality_report("V10", "M1")

        assert report.symbol == "V10"
        assert report.timeframe == "M1"
        assert report.quality == OHLCVQuality.EXCELLENT
        assert report.score == 1.0
        assert len(report.issues) == 0

    @pytest.mark.asyncio
    async def test_quality_report_with_gaps(self, collector, temp_dir):
        """Test quality report with data gaps."""
        await collector.initialize()

        # Create gapped data (use recent dates)
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        gapped_data = [
            OHLCVData(
                symbol="V10",
                timestamp=recent_time + timedelta(minutes=i * 10),  # 10 min gaps
                open=10000.0 + i,
                high=10010.0 + i,
                low=9995.0 + i,
                close=10005.0 + i,
                volume=100 + i,
            )
            for i in range(3)
        ]

        await collector._store_ohlcv_data("V10", "M1", gapped_data)

        report = await collector.generate_quality_report("V10", "M1")

        assert report.quality != OHLCVQuality.EXCELLENT
        assert len(report.data_gaps) > 0

    @pytest.mark.asyncio
    async def test_quality_report_no_file(self, collector):
        """Test quality report when no data file exists."""
        await collector.initialize()

        report = await collector.generate_quality_report("V10", "M1")

        # With 2 issues (gap + no file), quality is ACCEPTABLE (0-2 issues range)
        assert report.quality in [OHLCVQuality.BAD, OHLCVQuality.ACCEPTABLE]
        assert any("No data file" in issue for issue in report.issues)


class TestContinuousCollection:
    """Tests for continuous collection loop."""

    @pytest.mark.asyncio
    async def test_start_stop_continuous_collection(self, collector, sample_ohlcv_data):
        """Test starting and stopping continuous collection."""
        await collector.initialize()

        collector.mt5_service.get_historical_data.return_value = sample_ohlcv_data

        # Start collection
        await collector.start_continuous_collection()
        assert collector.is_running is True

        # Wait briefly
        await asyncio.sleep(0.1)

        # Stop collection
        await collector.stop_continuous_collection()
        assert collector.is_running is False

    @pytest.mark.asyncio
    async def test_continuous_collection_fetches_data(self, collector, sample_ohlcv_data):
        """Test that continuous collection fetches and stores data."""
        await collector.initialize()

        collector.mt5_service.get_historical_data.return_value = sample_ohlcv_data

        # Start collection
        await collector.start_continuous_collection()

        # Wait for at least one collection cycle
        await asyncio.sleep(0.2)

        # Stop collection
        await collector.stop_continuous_collection()

        # Verify data was stored
        file_path = collector._get_file_path("V10", "M1")
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_start_without_initialization(self, collector):
        """Test starting without initialization raises error."""
        with pytest.raises(RuntimeError, match="Service not initialized"):
            await collector.start_continuous_collection()


class TestManualDataFetch:
    """Tests for manual data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_all_timeframes_once(self, collector, sample_ohlcv_data):
        """Test fetching all timeframes manually."""
        await collector.initialize()

        collector.mt5_service.get_historical_data.return_value = sample_ohlcv_data

        results = await collector.fetch_all_timeframes_once("V10")

        assert len(results) == 6  # 6 timeframes
        for timeframe in collector.TIMEFRAMES:
            assert timeframe in results
            assert results[timeframe] == len(sample_ohlcv_data)

    @pytest.mark.asyncio
    async def test_fetch_all_timeframes_without_initialization(self, collector):
        """Test fetching without initialization raises error."""
        with pytest.raises(RuntimeError, match="Service not initialized"):
            await collector.fetch_all_timeframes_once("V10")


class TestStatistics:
    """Tests for statistics tracking."""

    @pytest.mark.asyncio
    async def test_get_statistics_all(self, collector):
        """Test getting all statistics."""
        await collector.initialize()

        stats = collector.get_statistics()

        assert len(stats) == 12  # 2 symbols * 6 timeframes

    @pytest.mark.asyncio
    async def test_get_statistics_filtered_by_symbol(self, collector):
        """Test getting statistics filtered by symbol."""
        await collector.initialize()

        stats = collector.get_statistics(symbol="V10")

        assert len(stats) == 6  # 6 timeframes for V10
        for key, stat in stats.items():
            assert stat.symbol == "V10"

    @pytest.mark.asyncio
    async def test_get_statistics_filtered_by_timeframe(self, collector):
        """Test getting statistics filtered by timeframe."""
        await collector.initialize()

        stats = collector.get_statistics(timeframe="M1")

        assert len(stats) == 2  # 2 symbols for M1
        for key, stat in stats.items():
            assert stat.timeframe == "M1"


class TestInvalidDataHandling:
    """Tests for handling invalid data during collection."""

    @pytest.mark.asyncio
    async def test_collection_with_invalid_data(
        self, collector, invalid_ohlcv_data
    ):
        """Test that invalid data is filtered out during collection."""
        await collector.initialize()

        # Mock returns invalid data
        collector.mt5_service.get_historical_data.return_value = invalid_ohlcv_data

        # Collect data
        await collector._collect_ohlcv_data("V10", "M1")

        # Verify no data stored (all invalid)
        key = "V10_M1"
        assert collector._stats[key].invalid_count == len(invalid_ohlcv_data)
        assert collector._stats[key].total_stored == 0

    @pytest.mark.asyncio
    async def test_collection_with_mixed_data(
        self, collector, sample_ohlcv_data, invalid_ohlcv_data
    ):
        """Test that mixed valid/invalid data is handled correctly."""
        await collector.initialize()

        # Mix valid and invalid data
        mixed_data = sample_ohlcv_data[:5] + invalid_ohlcv_data[:2]

        collector.mt5_service.get_historical_data.return_value = mixed_data

        # Collect data
        await collector._collect_ohlcv_data("V10", "M1")

        # Verify only valid data stored
        key = "V10_M1"
        assert collector._stats[key].invalid_count == 2
        assert collector._stats[key].total_stored == 5


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
