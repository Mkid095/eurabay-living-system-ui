"""
Tests for Data Ingestion Service - Continuous market data ingestion from MT5.

These tests verify the data ingestion service functionality including:
- Service initialization and configuration
- Async data fetching loops for tick and OHLCV data
- Graceful shutdown handling
- Data quality monitoring
- Data storage to SQLite and Parquet
- Backfill functionality

Uses mocking to simulate MT5 operations without requiring a live MT5 connection.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil

from app.services.data_ingestion_service import (
    DataIngestionService,
    DataQuality,
    DataQualityReport,
    IngestionStats,
)
from app.services.mt5_service import MT5Error, TickData, OHLCVData


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_mt5_service():
    """Create mock MT5 service."""
    service = AsyncMock()
    service.is_connected = True
    service.initialize = AsyncMock()
    return service


@pytest.fixture
def mock_database_service():
    """Create mock database service."""
    service = AsyncMock()
    service.create_market_data = AsyncMock()
    return service


@pytest.fixture
def mock_time_series_storage(temp_data_dir):
    """Create mock time series storage."""
    with patch('app.services.data_ingestion_service.TimeSeriesStorage') as mock:
        instance = MagicMock()
        instance.save_market_data = MagicMock()
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_settings(temp_data_dir):
    """Mock application settings."""
    with patch('app.services.data_ingestion_service.settings') as mock:
        mock.DATA_DIR = temp_data_dir
        mock.parsed_trading_symbols = ["V10", "V25", "V50", "V75", "V100"]
        yield mock


@pytest.fixture
def data_ingestion_service(mock_mt5_service, mock_database_service, mock_time_series_storage, mock_settings):
    """Create data ingestion service with mocked dependencies."""
    service = DataIngestionService(
        mt5_service=mock_mt5_service,
        database_service=mock_database_service,
        time_series_storage=None,  # Will be created in initialize
        symbols=["V10", "V25", "V50"],
    )
    return service


@pytest.fixture
def sample_tick_data():
    """Create sample tick data."""
    return TickData(
        symbol="V10",
        bid=100.50,
        ask=100.55,
        spread=0.05,
        volume=100,
        time=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data."""
    base_time = datetime.now(timezone.utc)
    return [
        OHLCVData(
            symbol="V10",
            timestamp=base_time - timedelta(minutes=i),
            open=100.0 + i,
            high=100.5 + i,
            low=99.5 + i,
            close=100.2 + i,
            volume=100 + i,
        )
        for i in range(10, 0, -1)
    ]


# ============================================================================
# Service Initialization Tests
# ============================================================================

class TestDataIngestionServiceInitialization:
    """Tests for data ingestion service initialization."""

    @pytest.mark.asyncio
    async def test_initialization_with_defaults(self, mock_settings):
        """Test service initialization with default parameters."""
        with patch('app.services.data_ingestion_service.MT5Service') as mock_mt5_class:
            mock_mt5 = AsyncMock()
            mock_mt5.is_connected = True
            mock_mt5_class.return_value = mock_mt5
            mock_mt5.initialize = AsyncMock()

            with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
                service = DataIngestionService()
                await service.initialize()

                assert service.is_initialized is True
                assert service.is_running is False
                mock_mt5.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_with_custom_symbols(self, mock_mt5_service, mock_settings):
        """Test service initialization with custom symbols."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            service = DataIngestionService(
                mt5_service=mock_mt5_service,
                symbols=["V10", "V25"]
            )
            await service.initialize()

            assert service.symbols == ["V10", "V25"]
            assert service.is_initialized is True

    @pytest.mark.asyncio
    async def test_initialization_failure_no_mt5_connection(self, mock_mt5_service, mock_settings):
        """Test initialization fails when MT5 is not connected."""
        mock_mt5_service.is_connected = False

        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            service = DataIngestionService(mt5_service=mock_mt5_service)

            with pytest.raises(RuntimeError, match="MT5 service is not connected"):
                await service.initialize()

    @pytest.mark.asyncio
    async def test_double_initialization(self, data_ingestion_service):
        """Test that double initialization is handled gracefully."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            assert data_ingestion_service.is_initialized is True

            # Second initialization should be ignored
            await data_ingestion_service.initialize()
            assert data_ingestion_service.is_initialized is True

    def test_default_constants(self):
        """Test default constant values."""
        assert DataIngestionService.TICK_INGESTION_INTERVAL == 1
        assert DataIngestionService.OHLCV_INGESTION_INTERVAL == 60
        assert DataIngestionService.TICK_DATA_RETENTION_DAYS == 7
        assert DataIngestionService.OHLCV_DATA_RETENTION_DAYS == 90
        assert "V10" in DataIngestionService.VOLATILITY_INDICES
        assert len(DataIngestionService.TIMEFRAMES) == 7


# ============================================================================
# Data Fetching Tests
# ============================================================================

class TestDataFetching:
    """Tests for data fetching functionality."""

    @pytest.mark.asyncio
    async def test_fetch_tick_data_success(self, data_ingestion_service, sample_tick_data):
        """Test successful tick data fetch."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)

            result = await data_ingestion_service._fetch_tick_data("V10")

            assert result is not None
            assert result.symbol == "V10"
            assert result.bid == 100.50

    @pytest.mark.asyncio
    async def test_fetch_tick_data_failure(self, data_ingestion_service):
        """Test tick data fetch failure handling."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(side_effect=MT5Error("Connection lost"))

            result = await data_ingestion_service._fetch_tick_data("V10")

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_success(self, data_ingestion_service, sample_ohlcv_data):
        """Test successful OHLCV data fetch."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

            result = await data_ingestion_service._fetch_ohlcv_data("V10", "M1", bars=100)

            assert result is not None
            assert len(result) == 10
            assert result[0].symbol == "V10"

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_invalid_timeframe(self, data_ingestion_service):
        """Test OHLCV data fetch with invalid timeframe."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            result = await data_ingestion_service._fetch_ohlcv_data("V10", "INVALID", bars=100)

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_data_all_timeframes(self, data_ingestion_service, sample_ohlcv_data):
        """Test OHLCV data fetch for all supported timeframes."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

            for timeframe in DataIngestionService.TIMEFRAMES:
                result = await data_ingestion_service._fetch_ohlcv_data("V10", timeframe, bars=100)
                assert result is not None, f"Failed for timeframe {timeframe}"


# ============================================================================
# Data Storage Tests
# ============================================================================

class TestDataStorage:
    """Tests for data storage functionality."""

    @pytest.mark.asyncio
    async def test_store_tick_data_success(self, data_ingestion_service, sample_tick_data):
        """Test successful tick data storage."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            await data_ingestion_service._store_tick_data(sample_tick_data)

            data_ingestion_service.database_service.create_market_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_tick_data_no_database(self, data_ingestion_service, sample_tick_data):
        """Test tick data storage when no database service is available."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            data_ingestion_service.database_service = None
            await data_ingestion_service.initialize()

            # Should not raise error
            await data_ingestion_service._store_tick_data(sample_tick_data)

    @pytest.mark.asyncio
    async def test_store_ohlcv_data_success(self, data_ingestion_service, sample_ohlcv_data):
        """Test successful OHLCV data storage."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage') as mock_storage_class:
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            await data_ingestion_service.initialize()

            await data_ingestion_service._store_ohlcv_data("V10", "M1", sample_ohlcv_data)

            mock_storage.save_market_data.assert_called()


# ============================================================================
# Ingestion Loop Tests
# ============================================================================

class TestIngestionLoops:
    """Tests for continuous ingestion loops."""

    @pytest.mark.asyncio
    async def test_tick_ingestion_loop_single_iteration(self, data_ingestion_service, sample_tick_data):
        """Test single iteration of tick ingestion loop."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)
            data_ingestion_service.database_service.create_market_data = AsyncMock()

            # Run loop for one iteration
            task = asyncio.create_task(data_ingestion_service._tick_ingestion_loop())
            await asyncio.sleep(0.1)  # Let it run briefly
            data_ingestion_service._stop_event.set()
            await task

            # Verify data was fetched and stored
            assert data_ingestion_service.mt5_service.get_price.called
            assert data_ingestion_service._stats.total_tick_records > 0

    @pytest.mark.asyncio
    async def test_ohlcv_ingestion_loop_single_iteration(self, data_ingestion_service, sample_ohlcv_data):
        """Test single iteration of OHLCV ingestion loop."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage') as mock_storage_class:
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

            # Run loop for one iteration
            task = asyncio.create_task(data_ingestion_service._ohlcv_ingestion_loop())
            await asyncio.sleep(0.1)
            data_ingestion_service._stop_event.set()
            await task

            # Verify data was fetched
            assert data_ingestion_service.mt5_service.get_historical_data.called

    @pytest.mark.asyncio
    async def test_quality_monitoring_loop(self, data_ingestion_service):
        """Test quality monitoring loop."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(
                return_value=TickData(
                    symbol="V10",
                    bid=100.0,
                    ask=100.1,
                    spread=0.1,
                    volume=100,
                    time=datetime.now(timezone.utc),
                )
            )
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=[])

            # Run loop for one iteration
            task = asyncio.create_task(data_ingestion_service._quality_monitoring_loop())
            await asyncio.sleep(0.1)
            data_ingestion_service._stop_event.set()
            await task

            # Verify quality reports were generated
            assert len(data_ingestion_service._quality_reports) > 0


# ============================================================================
# Start and Stop Tests
# ============================================================================

class TestStartStop:
    """Tests for starting and stopping ingestion."""

    @pytest.mark.asyncio
    async def test_start_continuous_ingestion(self, data_ingestion_service):
        """Test starting continuous ingestion."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            await data_ingestion_service.start_continuous_ingestion()

            assert data_ingestion_service.is_running is True
            assert data_ingestion_service._ingestion_tasks is not None
            assert len(data_ingestion_service._ingestion_tasks) == 4

            # Clean up
            await data_ingestion_service.stop_continuous_ingestion()

    @pytest.mark.asyncio
    async def test_start_without_initialization(self, data_ingestion_service):
        """Test starting ingestion without initialization raises error."""
        with pytest.raises(RuntimeError, match="Service not initialized"):
            await data_ingestion_service.start_continuous_ingestion()

    @pytest.mark.asyncio
    async def test_double_start(self, data_ingestion_service):
        """Test that double start is handled gracefully."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            await data_ingestion_service.start_continuous_ingestion()
            assert data_ingestion_service.is_running is True

            # Second start should be ignored
            await data_ingestion_service.start_continuous_ingestion()
            assert data_ingestion_service.is_running is True

            # Clean up
            await data_ingestion_service.stop_continuous_ingestion()

    @pytest.mark.asyncio
    async def test_stop_continuous_ingestion(self, data_ingestion_service):
        """Test stopping continuous ingestion."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            await data_ingestion_service.start_continuous_ingestion()
            assert data_ingestion_service.is_running is True

            await data_ingestion_service.stop_continuous_ingestion()

            assert data_ingestion_service.is_running is False
            assert data_ingestion_service._stop_event.is_set()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, data_ingestion_service):
        """Test stopping when not running is handled gracefully."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            # Should not raise error
            await data_ingestion_service.stop_continuous_ingestion()


# ============================================================================
# Quality Monitoring Tests
# ============================================================================

class TestQualityMonitoring:
    """Tests for data quality monitoring."""

    @pytest.mark.asyncio
    async def test_quality_report_excellent(self, data_ingestion_service, sample_tick_data):
        """Test quality report with excellent data."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(
                return_value=[
                    OHLCVData(
                        symbol="V10",
                        timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
                        open=100.0,
                        high=100.5,
                        low=99.5,
                        close=100.2,
                        volume=100,
                    )
                    for i in range(100)
                ]
            )

            report = await data_ingestion_service._generate_quality_report("V10")

            assert report.symbol == "V10"
            assert report.quality in [DataQuality.EXCELLENT, DataQuality.GOOD]

    @pytest.mark.asyncio
    async def test_quality_report_stale_data(self, data_ingestion_service):
        """Test quality report detects stale data."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            stale_tick = TickData(
                symbol="V10",
                bid=100.0,
                ask=100.1,
                spread=0.1,
                volume=100,
                time=datetime.now(timezone.utc) - timedelta(minutes=20),
            )
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=stale_tick)
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=[])

            report = await data_ingestion_service._generate_quality_report("V10")

            assert report.stale_data is True
            assert len(report.issues) > 0

    @pytest.mark.asyncio
    async def test_quality_report_no_data(self, data_ingestion_service):
        """Test quality report with no data available."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=None)
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=None)

            report = await data_ingestion_service._generate_quality_report("V10")

            # With 1 issue ("No data available"), quality is GOOD (score 0.8)
            assert report.quality == DataQuality.GOOD
            assert report.stale_data is True
            assert len(report.issues) > 0


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Tests for statistics tracking."""

    def test_get_statistics(self, data_ingestion_service):
        """Test getting current statistics."""
        stats = data_ingestion_service.get_statistics()

        assert isinstance(stats, IngestionStats)
        assert stats.symbols_ingested == 0
        assert stats.total_ohlcv_records == 0
        assert stats.total_tick_records == 0

    def test_statistics_updated_during_ingestion(self, data_ingestion_service, sample_tick_data):
        """Test statistics are updated during data ingestion."""
        data_ingestion_service._stats.total_tick_records = 100
        data_ingestion_service._stats.total_ohlcv_records = 1000

        stats = data_ingestion_service.get_statistics()

        assert stats.total_tick_records == 100
        assert stats.total_ohlcv_records == 1000


# ============================================================================
# Backfill Tests
# ============================================================================

class TestBackfill:
    """Tests for historical data backfill."""

    @pytest.mark.asyncio
    async def test_backfill_missing_data(self, data_ingestion_service, sample_ohlcv_data):
        """Test backfill of missing historical data."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

            start_date = datetime.now(timezone.utc) - timedelta(days=7)
            end_date = datetime.now(timezone.utc)

            count = await data_ingestion_service.backfill_missing_data(
                "V10", "M1", start_date, end_date
            )

            assert count > 0

    @pytest.mark.asyncio
    async def test_backfill_no_data_available(self, data_ingestion_service):
        """Test backfill when no data is available."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=None)

            start_date = datetime.now(timezone.utc) - timedelta(days=7)
            end_date = datetime.now(timezone.utc)

            count = await data_ingestion_service.backfill_missing_data(
                "V10", "M1", start_date, end_date
            )

            assert count == 0

    @pytest.mark.asyncio
    async def test_backfill_without_initialization(self, data_ingestion_service):
        """Test backfill without initialization raises error."""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)

        with pytest.raises(RuntimeError, match="Service not initialized"):
            await data_ingestion_service.backfill_missing_data(
                "V10", "M1", start_date
            )


# ============================================================================
# Manual Fetch Tests
# ============================================================================

class TestManualFetch:
    """Tests for manual data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_all_symbols_once(self, data_ingestion_service, sample_tick_data, sample_ohlcv_data):
        """Test manual fetch for all symbols."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

            results = await data_ingestion_service.fetch_all_symbols_once()

            assert len(results) == len(data_ingestion_service.symbols)
            for symbol in data_ingestion_service.symbols:
                assert symbol in results
                assert "tick" in results[symbol]
                assert "ohlcv" in results[symbol]

    @pytest.mark.asyncio
    async def test_fetch_all_symbols_error_handling(self, data_ingestion_service):
        """Test manual fetch with errors."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(side_effect=MT5Error("Error"))
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(side_effect=MT5Error("Error"))

            results = await data_ingestion_service.fetch_all_symbols_once()

            # Should complete without raising errors
            assert len(results) == len(data_ingestion_service.symbols)


# ============================================================================
# Integration Tests
# ============================================================================

class TestDataIngestionIntegration:
    """Integration tests for data ingestion service."""

    @pytest.mark.asyncio
    async def test_full_ingestion_cycle(self, data_ingestion_service, sample_tick_data, sample_ohlcv_data):
        """Test complete ingestion cycle from start to stop."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage') as mock_storage_class:
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            await data_ingestion_service.initialize()

            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv_data)

            # Start ingestion
            await data_ingestion_service.start_continuous_ingestion()
            assert data_ingestion_service.is_running is True

            # Let it run briefly
            await asyncio.sleep(0.2)

            # Stop ingestion
            await data_ingestion_service.stop_continuous_ingestion()
            assert data_ingestion_service.is_running is False

            # Verify statistics
            stats = data_ingestion_service.get_statistics()
            assert stats.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_graceful_shutdown_on_error(self, data_ingestion_service):
        """Test graceful shutdown when errors occur."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            # Mock to raise error
            data_ingestion_service.mt5_service.get_price = AsyncMock(side_effect=MT5Error("Connection lost"))

            await data_ingestion_service.start_continuous_ingestion()
            await asyncio.sleep(0.1)

            # Should stop gracefully
            await data_ingestion_service.stop_continuous_ingestion()

            assert data_ingestion_service.is_running is False
            # Errors are logged in the ingestion loop, verify service stopped cleanly

    @pytest.mark.asyncio
    async def test_multiple_symbols_concurrent_ingestion(self, data_ingestion_service, sample_tick_data):
        """Test concurrent ingestion for multiple symbols."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)

            # Fetch for all symbols
            tasks = [
                data_ingestion_service._fetch_tick_data(symbol)
                for symbol in data_ingestion_service.symbols
            ]
            results = await asyncio.gather(*tasks)

            # All symbols should have data
            assert len(results) == len(data_ingestion_service.symbols)

    @pytest.mark.asyncio
    async def test_data_quality_monitoring_integration(self, data_ingestion_service):
        """Test data quality monitoring integration."""
        with patch('app.services.data_ingestion_service.TimeSeriesStorage'):
            await data_ingestion_service.initialize()

            fresh_tick = TickData(
                symbol="V10",
                bid=100.0,
                ask=100.1,
                spread=0.1,
                volume=100,
                time=datetime.now(timezone.utc),
            )
            data_ingestion_service.mt5_service.get_price = AsyncMock(return_value=fresh_tick)
            data_ingestion_service.mt5_service.get_historical_data = AsyncMock(return_value=[])

            reports = data_ingestion_service.get_quality_reports()

            assert isinstance(reports, dict)
            # Reports will be populated by the monitoring loop
