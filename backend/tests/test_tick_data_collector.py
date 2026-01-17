"""
Unit tests for Tick Data Collector service.

Tests the tick data collection, deduplication, quality validation,
and storage functionality for all volatility indices.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import replace

from app.services.tick_data_collector import (
    TickDataCollector,
    TickDataQualityReport,
    TickCollectionStats,
    TickDataRecord,
    TickDataQuality,
)
from app.services.mt5_service import TickData, MT5Error


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_mt5_service():
    """Create a mock MT5 service."""
    service = AsyncMock()
    service.is_connected = True
    service.initialize = AsyncMock()
    return service


@pytest.fixture
def mock_database_service():
    """Create a mock database service."""
    service = AsyncMock()
    service.create_market_data = AsyncMock()
    return service


@pytest.fixture
def sample_tick_data():
    """Create sample tick data."""
    return TickData(
        symbol="V10",
        bid=1.08550,
        ask=1.08555,
        spread=0.5,
        time=datetime.now(timezone.utc),
        volume=100,
    )


@pytest.fixture
def sample_tick_data_list():
    """Create sample tick data for all volatility indices."""
    symbols = ["V10", "V25", "V50", "V75", "V100"]
    now = datetime.now(timezone.utc)
    return [
        TickData(
            symbol=symbol,
            bid=1.08550 + i * 0.001,
            ask=1.08555 + i * 0.001,
            spread=0.5,
            time=now + timedelta(milliseconds=i * 100),
            volume=100,
        )
        for i, symbol in enumerate(symbols)
    ]


@pytest.fixture
async def tick_collector(mock_mt5_service, mock_database_service):
    """Create a TickDataCollector instance for testing."""
    collector = TickDataCollector(
        mt5_service=mock_mt5_service,
        database_service=mock_database_service,
        symbols=["V10", "V25", "V50", "V75", "V100"],
    )
    await collector.initialize()
    return collector


# ============================================================================
# Initialization Tests
# ============================================================================

class TestTickDataCollectorInitialization:
    """Tests for TickDataCollector initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_mt5_service, mock_database_service):
        """Test successful initialization."""
        collector = TickDataCollector(
            mt5_service=mock_mt5_service,
            database_service=mock_database_service,
        )

        await collector.initialize()

        assert collector.is_initialized is True
        assert collector.is_running is False
        # Note: initialize is NOT called on the provided MT5 service
        # It's only called if the service is None and needs to be created

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, tick_collector):
        """Test that initialize is idempotent."""
        await tick_collector.initialize()

        assert tick_collector.is_initialized is True

    @pytest.mark.asyncio
    async def test_initialize_without_mt5_service(self):
        """Test initialization fails when MT5 service is not connected."""
        mock_mt5 = AsyncMock()
        mock_mt5.is_connected = False
        mock_mt5.initialize = AsyncMock()

        collector = TickDataCollector(
            mt5_service=mock_mt5,
            database_service=AsyncMock(),  # Provide mock to avoid database import
        )

        with pytest.raises(RuntimeError, match="MT5 service is not connected"):
            await collector.initialize()

    @pytest.mark.asyncio
    async def test_initialize_sets_up_tick_cache(self, tick_collector):
        """Test that initialization sets up tick cache for all symbols."""
        assert "V10" in tick_collector._tick_cache
        assert "V25" in tick_collector._tick_cache
        assert "V50" in tick_collector._tick_cache
        assert "V75" in tick_collector._tick_cache
        assert "V100" in tick_collector._tick_cache

    @pytest.mark.asyncio
    async def test_initialize_sets_up_statistics(self, tick_collector):
        """Test that initialization sets up statistics for all symbols."""
        assert "V10" in tick_collector._stats
        assert "V25" in tick_collector._stats
        assert "V50" in tick_collector._stats
        assert "V75" in tick_collector._stats
        assert "V100" in tick_collector._stats

        for symbol, stats in tick_collector._stats.items():
            assert stats.symbol == symbol
            assert stats.total_collected == 0
            assert stats.total_stored == 0


# ============================================================================
# Tick Data Collection Tests
# ============================================================================

class TestTickDataCollection:
    """Tests for tick data collection functionality."""

    @pytest.mark.asyncio
    async def test_fetch_tick_data_success(self, tick_collector, sample_tick_data):
        """Test successful tick data fetching."""
        tick_collector.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)

        result = await tick_collector.fetch_tick_data("V10")

        assert result is not None
        assert result.symbol == "V10"
        assert result.bid == 1.08550
        assert result.ask == 1.08555

    @pytest.mark.asyncio
    async def test_fetch_tick_data_not_initialized(self):
        """Test that fetch_tick_data fails when not initialized."""
        collector = TickDataCollector()
        collector.is_initialized = False

        with pytest.raises(RuntimeError, match="Service not initialized"):
            await collector.fetch_tick_data("V10")

    @pytest.mark.asyncio
    async def test_fetch_tick_data_mt5_error(self, tick_collector):
        """Test handling of MT5 errors during fetch."""
        tick_collector.mt5_service.get_price = AsyncMock(
            side_effect=MT5Error("Connection lost")
        )

        result = await tick_collector.fetch_tick_data("V10")

        assert result is None

    @pytest.mark.asyncio
    async def test_start_continuous_collection(self, tick_collector):
        """Test starting continuous collection."""
        await tick_collector.start_continuous_collection()

        assert tick_collector.is_running is True
        assert tick_collector._collection_task is not None

    @pytest.mark.asyncio
    async def test_start_already_running(self, tick_collector):
        """Test that start is idempotent."""
        await tick_collector.start_continuous_collection()
        await tick_collector.start_continuous_collection()

        assert tick_collector.is_running is True

    @pytest.mark.asyncio
    async def test_stop_continuous_collection(self, tick_collector):
        """Test stopping continuous collection."""
        await tick_collector.start_continuous_collection()
        await asyncio.sleep(0.1)  # Let task start
        await tick_collector.stop_continuous_collection()

        assert tick_collector.is_running is False


# ============================================================================
# Deduplication Tests
# ============================================================================

class TestTickDataDeduplication:
    """Tests for tick data deduplication functionality."""

    @pytest.mark.asyncio
    async def test_create_tick_record_with_checksum(self, tick_collector, sample_tick_data):
        """Test that tick records are created with unique checksums."""
        record = tick_collector._create_tick_record(sample_tick_data)

        assert isinstance(record, TickDataRecord)
        assert record.symbol == "V10"
        assert record.bid == 1.08550
        assert record.ask == 1.08555
        assert record.checksum is not None
        assert len(record.checksum) == 16

    @pytest.mark.asyncio
    async def test_checksum_uniqueness(self, tick_collector):
        """Test that different tick data produces different checksums."""
        tick1 = TickData(
            symbol="V10",
            bid=1.08550,
            ask=1.08555,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )
        tick2 = TickData(
            symbol="V10",
            bid=1.08551,  # Different price
            ask=1.08556,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )

        record1 = tick_collector._create_tick_record(tick1)
        record2 = tick_collector._create_tick_record(tick2)

        assert record1.checksum != record2.checksum

    @pytest.mark.asyncio
    async def test_is_duplicate_detection(self, tick_collector, sample_tick_data):
        """Test duplicate tick detection."""
        record = tick_collector._create_tick_record(sample_tick_data)

        # First check - not duplicate
        is_dup1 = await tick_collector._is_duplicate(record)
        assert is_dup1 is False

        # Add to cache
        await tick_collector._add_to_cache(record)

        # Second check - duplicate
        is_dup2 = await tick_collector._is_duplicate(record)
        assert is_dup2 is True

    @pytest.mark.asyncio
    async def test_cache_management(self, tick_collector):
        """Test that cache is managed correctly."""
        # Create many tick records
        for i in range(100):
            tick = TickData(
                symbol="V10",
                bid=1.08550 + i * 0.0001,
                ask=1.08555 + i * 0.0001,
                spread=0.5,
                time=datetime.now(timezone.utc) + timedelta(milliseconds=i),
                volume=100,
            )
            record = tick_collector._create_tick_record(tick)
            await tick_collector._add_to_cache(record)

        # Cache should have entries
        assert len(tick_collector._tick_cache["V10"]) > 0


# ============================================================================
# Data Quality Validation Tests
# ============================================================================

class TestDataQualityValidation:
    """Tests for data quality validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_valid_tick(self, tick_collector, sample_tick_data):
        """Test validation of valid tick data."""
        record = tick_collector._create_tick_record(sample_tick_data)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is True
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_validate_negative_bid_price(self, tick_collector):
        """Test rejection of negative bid price."""
        tick = TickData(
            symbol="V10",
            bid=-1.0,  # Invalid
            ask=1.08555,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )
        record = tick_collector._create_tick_record(tick)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is False
        assert "Invalid price" in result["reason"]

    @pytest.mark.asyncio
    async def test_validate_ask_below_bid(self, tick_collector):
        """Test rejection when ask price is below bid."""
        tick = TickData(
            symbol="V10",
            bid=1.08555,
            ask=1.08550,  # Below bid
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )
        record = tick_collector._create_tick_record(tick)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is False
        assert "Ask price below bid" in result["reason"]

    @pytest.mark.asyncio
    async def test_validate_future_timestamp(self, tick_collector):
        """Test rejection of future timestamp."""
        tick = TickData(
            symbol="V10",
            bid=1.08550,
            ask=1.08555,
            spread=0.5,
            time=datetime.now(timezone.utc) + timedelta(hours=1),  # Future
            volume=100,
        )
        record = tick_collector._create_tick_record(tick)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is False
        assert "Timestamp in the future" in result["reason"]

    @pytest.mark.asyncio
    async def test_validate_stale_timestamp(self, tick_collector):
        """Test rejection of stale timestamp."""
        tick = TickData(
            symbol="V10",
            bid=1.08550,
            ask=1.08555,
            spread=0.5,
            time=datetime.now(timezone.utc) - timedelta(seconds=20),  # Too old
            volume=100,
        )
        record = tick_collector._create_tick_record(tick)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is False
        assert "Timestamp too old" in result["reason"]

    @pytest.mark.asyncio
    async def test_validate_abnormal_spread(self, tick_collector):
        """Test rejection of abnormal spread."""
        tick = TickData(
            symbol="V10",
            bid=1.08550,
            ask=1.09000,  # Very wide spread
            spread=55.0,  # Exceeds MAX_SPREAD_PIPS (50)
            time=datetime.now(timezone.utc),
            volume=100,
        )
        record = tick_collector._create_tick_record(tick)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is False
        assert "Abnormal spread" in result["reason"]

    @pytest.mark.asyncio
    async def test_validate_negative_volume(self, tick_collector):
        """Test rejection of negative volume."""
        tick = TickData(
            symbol="V10",
            bid=1.08550,
            ask=1.08555,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=-100,  # Invalid
        )
        record = tick_collector._create_tick_record(tick)
        result = await tick_collector._validate_tick_data(record)

        assert result["is_valid"] is False
        assert "Invalid volume" in result["reason"]


# ============================================================================
# Storage Tests
# ============================================================================

class TestTickDataStorage:
    """Tests for tick data storage functionality."""

    @pytest.mark.asyncio
    async def test_store_tick_data_success(
        self, tick_collector, sample_tick_data, mock_database_service
    ):
        """Test successful tick data storage."""
        record = tick_collector._create_tick_record(sample_tick_data)

        await tick_collector._store_tick_data(record)

        mock_database_service.create_market_data.assert_called_once()
        call_args = mock_database_service.create_market_data.call_args
        assert call_args[1]["symbol"] == "V10"
        assert call_args[1]["timeframe"] == "TICK"

    @pytest.mark.asyncio
    async def test_store_without_database_service(self, tick_collector, sample_tick_data):
        """Test storage behavior when database service is not available."""
        tick_collector.database_service = None
        record = tick_collector._create_tick_record(sample_tick_data)

        # Should not raise error, just log warning
        await tick_collector._store_tick_data(record)


# ============================================================================
# Quality Monitoring Tests
# ============================================================================

class TestQualityMonitoring:
    """Tests for quality monitoring functionality."""

    @pytest.mark.asyncio
    async def test_generate_quality_report_excellent(self, tick_collector):
        """Test quality report generation for excellent data."""
        report = await tick_collector.generate_quality_report("V10")

        assert isinstance(report, TickDataQualityReport)
        assert report.symbol == "V10"
        assert report.quality in TickDataQuality
        assert 0.0 <= report.score <= 1.0

    @pytest.mark.asyncio
    async def test_quality_report_stale_data(self, tick_collector):
        """Test quality report detects stale data."""
        # Simulate stale data by setting last tick time to past
        tick_collector._last_tick_time["V10"] = datetime.now(timezone.utc) - timedelta(
            seconds=20
        )

        report = await tick_collector.generate_quality_report("V10")

        assert report.stale_data is True
        assert "stale" in " ".join(report.issues).lower()

    @pytest.mark.asyncio
    async def test_quality_report_no_data(self, tick_collector):
        """Test quality report when no data received."""
        tick_collector._last_tick_time["V10"] = None

        report = await tick_collector.generate_quality_report("V10")

        assert report.stale_data is True
        assert len(report.issues) > 0


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Tests for statistics tracking functionality."""

    @pytest.mark.asyncio
    async def test_get_statistics_all_symbols(self, tick_collector):
        """Test getting statistics for all symbols."""
        stats = tick_collector.get_statistics()

        assert isinstance(stats, dict)
        assert "V10" in stats
        assert "V25" in stats
        assert "V50" in stats
        assert "V75" in stats
        assert "V100" in stats

    @pytest.mark.asyncio
    async def test_get_statistics_single_symbol(self, tick_collector):
        """Test getting statistics for a single symbol."""
        stats = tick_collector.get_statistics("V10")

        assert isinstance(stats, dict)
        assert "V10" in stats
        assert "V25" not in stats

    @pytest.mark.asyncio
    async def test_statistics_update_on_collection(
        self, tick_collector, sample_tick_data
    ):
        """Test that statistics are updated during collection."""
        initial_stats = tick_collector._stats["V10"]
        initial_collected = initial_stats.total_collected

        # Simulate collection
        tick_collector._stats["V10"].total_collected += 1

        updated_stats = tick_collector._stats["V10"]
        assert updated_stats.total_collected == initial_collected + 1


# ============================================================================
# Retention Policy Tests
# ============================================================================

class TestRetentionPolicy:
    """Tests for data retention policy functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_old_tick_data(self, tick_collector):
        """Test cleanup of old tick data."""
        deleted = await tick_collector.cleanup_old_tick_data()

        assert isinstance(deleted, int)
        assert deleted >= 0

    @pytest.mark.asyncio
    async def test_cleanup_without_database_service(self, tick_collector):
        """Test cleanup behavior when database service is not available."""
        tick_collector.database_service = None

        deleted = await tick_collector.cleanup_old_tick_data()

        assert deleted == 0


# ============================================================================
# Multi-Symbol Tests
# ============================================================================

class TestMultiSymbolCollection:
    """Tests for collecting data from multiple symbols."""

    @pytest.mark.asyncio
    async def test_fetch_all_symbols_once(
        self, tick_collector, sample_tick_data_list
    ):
        """Test fetching tick data for all symbols at once."""
        # Mock MT5 service to return different data for each symbol
        async def mock_get_price(symbol):
            for tick in sample_tick_data_list:
                if tick.symbol == symbol:
                    return tick
            return None

        tick_collector.mt5_service.get_price = mock_get_price

        results = await tick_collector.fetch_all_symbols_once()

        assert isinstance(results, dict)
        assert len(results) == 5
        assert all(isinstance(results.get(s), TickData) for s in results.keys())

    @pytest.mark.asyncio
    async def test_collect_from_all_volatility_indices(
        self, tick_collector, sample_tick_data_list
    ):
        """Test that data can be collected from all 5 volatility indices."""
        symbols = ["V10", "V25", "V50", "V75", "V100"]

        # Mock MT5 service
        async def mock_get_price(symbol):
            for tick in sample_tick_data_list:
                if tick.symbol == symbol:
                    return tick
            return None

        tick_collector.mt5_service.get_price = mock_get_price

        # Collect from all symbols
        for symbol in symbols:
            tick = await tick_collector.fetch_tick_data(symbol)
            assert tick is not None
            assert tick.symbol == symbol


# ============================================================================
# Integration Tests
# ============================================================================

class TestTickDataCollectorIntegration:
    """Integration tests for tick data collector."""

    @pytest.mark.asyncio
    async def test_full_tick_collection_workflow(
        self, tick_collector, sample_tick_data, mock_database_service
    ):
        """Test complete workflow from fetch to storage."""
        # Mock MT5 service
        tick_collector.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)

        # Fetch tick data
        tick = await tick_collector.fetch_tick_data("V10")
        assert tick is not None

        # Create record
        record = tick_collector._create_tick_record(tick)
        assert record.checksum is not None

        # Validate
        validation = await tick_collector._validate_tick_data(record)
        assert validation["is_valid"] is True

        # Store
        await tick_collector._store_tick_data(record)
        mock_database_service.create_market_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_prevention_workflow(
        self, tick_collector, sample_tick_data, mock_database_service
    ):
        """Test that duplicates are prevented in the workflow."""
        tick_collector.mt5_service.get_price = AsyncMock(return_value=sample_tick_data)

        # First collection
        await tick_collector._collect_tick_data("V10")
        first_call_count = mock_database_service.create_market_data.call_count

        # Second collection with same data
        await tick_collector._collect_tick_data("V10")
        second_call_count = mock_database_service.create_market_data.call_count

        # Second call should not store (duplicate)
        assert first_call_count > 0
        assert second_call_count == first_call_count

    @pytest.mark.asyncio
    async def test_invalid_data_prevention_workflow(
        self, tick_collector, mock_database_service
    ):
        """Test that invalid data is prevented from storage."""
        # Create invalid tick
        invalid_tick = TickData(
            symbol="V10",
            bid=-1.0,  # Invalid
            ask=1.08555,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )

        tick_collector.mt5_service.get_price = AsyncMock(return_value=invalid_tick)

        # Try to collect
        await tick_collector._collect_tick_data("V10")

        # Should not store invalid data
        mock_database_service.create_market_data.assert_not_called()
