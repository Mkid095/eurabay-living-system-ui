"""
Test suite for DataIngestionService.

Tests data ingestion functionality including:
- Service initialization
- Tick data ingestion
- OHLCV data ingestion
- Data quality checks
- Retention policy cleanup
- Backfill functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd

from app.services.data_ingestion_service import (
    DataIngestionService,
    DataQuality,
    DataQualityReport,
    IngestionStats,
)
from app.services.mt5_service import TickData, OHLCVData, MT5Error


@pytest.fixture
def mock_mt5_service():
    """Create mock MT5 service."""
    service = AsyncMock()
    service.is_connected = True
    return service


@pytest.fixture
def mock_database_service():
    """Create mock database service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_time_series_storage():
    """Create mock time series storage."""
    storage = Mock()
    return storage


@pytest.fixture
def sample_tick_data():
    """Create sample tick data."""
    return TickData(
        symbol="V10",
        bid=10000.5,
        ask=10001.0,
        spread=0.5,
        time=datetime.now(timezone.utc),
        volume=100,
    )


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data."""
    base_time = datetime.now(timezone.utc)
    return [
        OHLCVData(
            symbol="V10",
            timestamp=base_time - timedelta(minutes=i),
            open=10000.0 + i,
            high=10005.0 + i,
            low=9995.0 + i,
            close=10002.0 + i,
            volume=100 + i,
        )
        for i in range(100, 0, -1)
    ]


@pytest.fixture
def data_ingestion_service(
    mock_mt5_service, mock_database_service, mock_time_series_storage
):
    """Create data ingestion service with mocked dependencies."""
    service = DataIngestionService(
        mt5_service=mock_mt5_service,
        database_service=mock_database_service,
        time_series_storage=mock_time_series_storage,
        symbols=["V10", "V25"],
    )
    return service


class TestInitialization:
    """Tests for DataIngestionService initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, data_ingestion_service):
        """Test successful initialization."""
        await data_ingestion_service.initialize()

        assert data_ingestion_service.is_initialized is True
        assert data_ingestion_service.is_running is False

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, data_ingestion_service, caplog
    ):
        """Test initializing when already initialized."""
        await data_ingestion_service.initialize()
        await data_ingestion_service.initialize()

        assert "already initialized" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_initialize_mt5_not_connected(self, mock_mt5_service):
        """Test initialization fails when MT5 not connected."""
        mock_mt5_service.is_connected = False

        service = DataIngestionService(mt5_service=mock_mt5_service)

        with pytest.raises(RuntimeError, match="not connected"):
            await service.initialize()

    def test_initialization_with_custom_symbols(self):
        """Test initialization with custom symbols."""
        service = DataIngestionService(symbols=["V10", "V50", "V100"])

        assert service.symbols == ["V10", "V50", "V100"]


class TestTickDataIngestion:
    """Tests for tick data ingestion."""

    @pytest.mark.asyncio
    async def test_fetch_tick_data_success(
        self, data_ingestion_service, sample_tick_data, mock_mt5_service
    ):
        """Test successful tick data fetch."""
        mock_mt5_service.get_price = AsyncMock(return_value=sample_tick_data)

        await data_ingestion_service.initialize()
        result = await data_ingestion_service._fetch_tick_data("V10")

        assert result is not None
        assert result.symbol == "V10"
        assert result.bid == 10000.5

    @pytest.mark.asyncio
    async def test_fetch_tick_data_failure(
        self, data_ingestion_service, mock_mt5_service, caplog
    ):
        """Test tick data fetch failure."""
        mock_mt5_service.get_price = AsyncMock(side_effect=MT5Error("Connection lost"))

        await data_ingestion_service.initialize()
        result = await data_ingestion_service._fetch_tick_data("V10")

        assert result is None
        assert "Failed to fetch tick data" in caplog.text

    @pytest.mark.asyncio
    async def test_store_tick_data(
        self,
        data_ingestion_service,
        sample_tick_data,
        mock_database_service,
    ):
        """Test storing tick data to database."""
        await data_ingestion_service.initialize()

        # Mock the market data creation
        with patch("app.services.data_ingestion_service.MarketData") as mock_market_data:
            mock_market_data.return_value = Mock()

            await data_ingestion_service._store_tick_data(sample_tick_data)

            # Verify database service was called
            mock_database_service.create_market_data.assert_called_once()


class TestOHLCVDataIngestion:
    """Tests for OHLCV data ingestion."""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_success(
        self, data_ingestion_service, sample_ohlcv_data, mock_mt5_service
    ):
        """Test successful OHLCV data fetch."""
        mock_mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

        await data_ingestion_service.initialize()
        result = await data_ingestion_service._fetch_ohlcv_data("V10", "M1", 100)

        assert result is not None
        assert len(result) == 100
        assert result[0].symbol == "V10"

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_invalid_timeframe(
        self, data_ingestion_service, caplog
    ):
        """Test OHLCV fetch with invalid timeframe."""
        await data_ingestion_service.initialize()
        result = await data_ingestion_service._fetch_ohlcv_data("V10", "INVALID", 100)

        assert result is None
        assert "Invalid timeframe" in caplog.text

    @pytest.mark.asyncio
    async def test_store_ohlcv_data(
        self,
        data_ingestion_service,
        sample_ohlcv_data,
        mock_time_series_storage,
        tmp_path,
    ):
        """Test storing OHLCV data to Parquet."""
        await data_ingestion_service.initialize()

        # Mock TimeSeriesStorage
        with patch("app.services.data_ingestion_service.TimeSeriesStorage") as mock_storage:
            mock_storage_instance = Mock()
            mock_storage.return_value = mock_storage_instance

            await data_ingestion_service._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

            # Verify save_market_data was called
            mock_storage_instance.save_market_data.assert_called_once()


class TestDataQuality:
    """Tests for data quality monitoring."""

    @pytest.mark.asyncio
    async def test_quality_report_excellent(
        self, data_ingestion_service, sample_tick_data, sample_ohlcv_data, mock_mt5_service
    ):
        """Test quality report for excellent data."""
        mock_mt5_service.get_price = AsyncMock(return_value=sample_tick_data)
        mock_mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

        await data_ingestion_service.initialize()
        report = await data_ingestion_service._generate_quality_report("V10")

        assert report.symbol == "V10"
        assert report.quality in [DataQuality.EXCELLENT, DataQuality.GOOD]
        assert report.score >= 0.8

    @pytest.mark.asyncio
    async def test_quality_report_stale_data(
        self, data_ingestion_service, mock_mt5_service, caplog
    ):
        """Test quality report detects stale data."""
        # Create old tick data
        old_tick = TickData(
            symbol="V10",
            bid=10000.5,
            ask=10001.0,
            spread=0.5,
            time=datetime.now(timezone.utc) - timedelta(minutes=20),
            volume=100,
        )
        mock_mt5_service.get_price = AsyncMock(return_value=old_tick)
        mock_mt5_service.get_historical_data = AsyncMock(return_value=[])

        await data_ingestion_service.initialize()
        report = await data_ingestion_service._generate_quality_report("V10")

        assert report.stale_data is True
        assert "stale" in " ".join(report.issues).lower()

    @pytest.mark.asyncio
    async def test_quality_report_no_data(
        self, data_ingestion_service, mock_mt5_service
    ):
        """Test quality report when no data available."""
        mock_mt5_service.get_price = AsyncMock(return_value=None)
        mock_mt5_service.get_historical_data = AsyncMock(return_value=None)

        await data_ingestion_service.initialize()
        report = await data_ingestion_service._generate_quality_report("V10")

        assert report.stale_data is True
        assert len(report.issues) > 0


class TestRetentionCleanup:
    """Tests for data retention cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_old_data(
        self, data_ingestion_service, tmp_path, caplog
    ):
        """Test cleanup of old data files."""
        await data_ingestion_service.initialize()

        # Create test Parquet files
        base_path = tmp_path / "market" / "V10" / "M1"
        base_path.mkdir(parents=True, exist_ok=True)

        # Create old file
        old_file = base_path / "2023-01-01.parquet"
        old_file.write_text("old data")

        # Create recent file
        recent_file = base_path / datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".parquet"
        recent_file.write_text("recent data")

        with patch("app.services.data_ingestion_service.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)
            await data_ingestion_service._cleanup_old_data()

        # Old file should be deleted
        assert not old_file.exists()
        # Recent file should still exist
        assert recent_file.exists()


class TestBackfill:
    """Tests for backfill functionality."""

    @pytest.mark.asyncio
    async def test_backfill_missing_data(
        self, data_ingestion_service, sample_ohlcv_data, mock_mt5_service
    ):
        """Test backfill of missing historical data."""
        mock_mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

        await data_ingestion_service.initialize()

        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        with patch.object(data_ingestion_service, "_store_ohlcv_data") as mock_store:
            count = await data_ingestion_service.backfill_missing_data(
                "V10", "M1", start_date, end_date
            )

            assert count > 0
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_backfill_no_data_available(
        self, data_ingestion_service, mock_mt5_service
    ):
        """Test backfill when no data available."""
        mock_mt5_service.get_historical_data = AsyncMock(return_value=None)

        await data_ingestion_service.initialize()

        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        count = await data_ingestion_service.backfill_missing_data(
            "V10", "M1", start_date, end_date
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_backfill_not_initialized(self, data_ingestion_service):
        """Test backfill fails when service not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await data_ingestion_service.backfill_missing_data(
                "V10", "M1", datetime.now(timezone.utc)
            )


class TestManualFetch:
    """Tests for manual data fetch functionality."""

    @pytest.mark.asyncio
    async def test_fetch_all_symbols_once(
        self, data_ingestion_service, sample_tick_data, sample_ohlcv_data, mock_mt5_service
    ):
        """Test manual fetch for all symbols."""
        mock_mt5_service.get_price = AsyncMock(return_value=sample_tick_data)
        mock_mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

        await data_ingestion_service.initialize()

        with patch.object(data_ingestion_service, "_store_tick_data"), patch.object(
            data_ingestion_service, "_store_ohlcv_data"
        ):
            results = await data_ingestion_service.fetch_all_symbols_once()

            assert "V10" in results
            assert "V25" in results
            assert results["V10"]["tick"] == 1
            assert results["V10"]["ohlcv"] == 100

    @pytest.mark.asyncio
    async def test_fetch_all_symbols_not_initialized(self, data_ingestion_service):
        """Test manual fetch fails when not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await data_ingestion_service.fetch_all_symbols_once()


class TestStatistics:
    """Tests for statistics tracking."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, data_ingestion_service):
        """Test getting ingestion statistics."""
        await data_ingestion_service.initialize()

        stats = data_ingestion_service.get_statistics()

        assert isinstance(stats, IngestionStats)
        assert stats.symbols_ingested == 0
        assert stats.total_ohlcv_records == 0
        assert stats.total_tick_records == 0

    @pytest.mark.asyncio
    async def test_get_quality_reports(self, data_ingestion_service):
        """Test getting quality reports."""
        await data_ingestion_service.initialize()

        reports = data_ingestion_service.get_quality_reports()

        assert isinstance(reports, dict)


class TestContinuousIngestion:
    """Tests for continuous ingestion loops."""

    @pytest.mark.asyncio
    async def test_start_continuous_ingestion(
        self, data_ingestion_service, mock_mt5_service
    ):
        """Test starting continuous ingestion."""
        mock_mt5_service.get_price = AsyncMock(return_value=None)
        mock_mt5_service.get_historical_data = AsyncMock(return_value=None)

        await data_ingestion_service.initialize()
        await data_ingestion_service.start_continuous_ingestion()

        assert data_ingestion_service.is_running is True
        assert data_ingestion_service._ingestion_tasks is not None
        assert len(data_ingestion_service._ingestion_tasks) == 4

        # Stop ingestion
        await data_ingestion_service.stop_continuous_ingestion()

    @pytest.mark.asyncio
    async def test_stop_continuous_ingestion(self, data_ingestion_service):
        """Test stopping continuous ingestion."""
        await data_ingestion_service.initialize()

        # Start ingestion
        with patch.object(data_ingestion_service, "_tick_ingestion_loop"), patch.object(
            data_ingestion_service, "_ohlcv_ingestion_loop"
        ), patch.object(data_ingestion_service, "_quality_monitoring_loop"), patch.object(
            data_ingestion_service, "_retention_cleanup_loop"
        ):
            await data_ingestion_service.start_continuous_ingestion()
            assert data_ingestion_service.is_running is True

            # Stop ingestion
            await data_ingestion_service.stop_continuous_ingestion()

            assert data_ingestion_service.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, data_ingestion_service, caplog):
        """Test starting when already running."""
        await data_ingestion_service.initialize()

        with patch.object(data_ingestion_service, "_tick_ingestion_loop"), patch.object(
            data_ingestion_service, "_ohlcv_ingestion_loop"
        ), patch.object(data_ingestion_service, "_quality_monitoring_loop"), patch.object(
            data_ingestion_service, "_retention_cleanup_loop"
        ):
            await data_ingestion_service.start_continuous_ingestion()
            await data_ingestion_service.start_continuous_ingestion()

            assert "already running" in caplog.text.lower()

            await data_ingestion_service.stop_continuous_ingestion()

    @pytest.mark.asyncio
    async def test_start_not_initialized(self, data_ingestion_service):
        """Test starting fails when not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await data_ingestion_service.start_continuous_ingestion()


class TestErrorHandling:
    """Tests for error handling and recovery."""

    @pytest.mark.asyncio
    async def test_tick_loop_error_recovery(
        self, data_ingestion_service, mock_mt5_service, caplog
    ):
        """Test tick loop recovers from errors."""
        # First call fails, second succeeds
        mock_mt5_service.get_price = AsyncMock(
            side_effect=[MT5Error("Network error"), Mock()]
        )

        await data_ingestion_service.initialize()

        # Run one iteration of the loop
        task = asyncio.create_task(data_ingestion_service._tick_ingestion_loop())

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop the loop
        data_ingestion_service._stop_event.set()
        await task

        # Should have logged error but continued
        assert any("Network error" in str(e) for e in data_ingestion_service._stats.errors)


class TestDataQualityReport:
    """Tests for DataQualityReport dataclass."""

    def test_quality_report_creation(self):
        """Test creating a quality report."""
        report = DataQualityReport(
            symbol="V10",
            timestamp=datetime.now(timezone.utc),
            quality=DataQuality.GOOD,
            missing_data_points=0,
            duplicate_data_points=0,
            outlier_data_points=0,
            stale_data=False,
            gaps_detected=0,
            score=0.8,
        )

        assert report.symbol == "V10"
        assert report.quality == DataQuality.GOOD
        assert report.score == 0.8


class TestIngestionStats:
    """Tests for IngestionStats dataclass."""

    def test_ingestion_stats_creation(self):
        """Test creating ingestion stats."""
        stats = IngestionStats(
            symbols_ingested=2,
            total_ohlcv_records=1000,
            total_tick_records=500,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=60.0,
        )

        assert stats.symbols_ingested == 2
        assert stats.total_ohlcv_records == 1000
        assert stats.total_tick_records == 500
        assert stats.duration_seconds == 60.0
