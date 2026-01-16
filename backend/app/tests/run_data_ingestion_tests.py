"""
Simple test runner for DataIngestionService tests.

Run this file to execute tests: python run_data_ingestion_tests.py
"""

import sys
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.services.data_ingestion_service import (
    DataIngestionService,
    DataQuality,
    DataQualityReport,
)
from app.services.mt5_service import TickData, OHLCVData


async def run_basic_tests():
    """Run basic functionality tests."""
    print("=" * 60)
    print("DataIngestionService - Basic Tests")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Service initialization
    print("\n[Test 1] Service initialization...")
    try:
        mock_mt5 = Mock()
        mock_mt5.is_connected = True

        service = DataIngestionService(
            mt5_service=mock_mt5,
            database_service=None,
            time_series_storage=None,
            symbols=["V10", "V25"],
        )

        await service.initialize()
        assert service.is_initialized is True
        assert service.is_running is False
        assert service.symbols == ["V10", "V25"]

        print("  PASSED: Service initializes correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 2: Tick data fetch
    print("\n[Test 2] Tick data fetch...")
    try:
        sample_tick = TickData(
            symbol="V10",
            bid=10000.5,
            ask=10001.0,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )

        mock_mt5.get_price = AsyncMock(return_value=sample_tick)

        result = await service._fetch_tick_data("V10")
        assert result is not None
        assert result.symbol == "V10"
        assert result.bid == 10000.5

        print("  PASSED: Tick data fetched correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 3: OHLCV data fetch
    print("\n[Test 3] OHLCV data fetch...")
    try:
        base_time = datetime.now(timezone.utc)
        sample_ohlcv = [
            OHLCVData(
                symbol="V10",
                timestamp=base_time - timedelta(minutes=i),
                open=10000.0 + i,
                high=10005.0 + i,
                low=9995.0 + i,
                close=10002.0 + i,
                volume=100 + i,
            )
            for i in range(10, 0, -1)
        ]

        mock_mt5.get_historical_data = AsyncMock(return_value=sample_ohlcv)

        result = await service._fetch_ohlcv_data("V10", "M1", 10)
        assert result is not None
        assert len(result) == 10
        assert result[0].symbol == "V10"

        print("  PASSED: OHLCV data fetched correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 4: Quality report generation
    print("\n[Test 4] Quality report generation...")
    try:
        # Create fresh tick data
        fresh_tick = TickData(
            symbol="V10",
            bid=10000.5,
            ask=10001.0,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )

        mock_mt5.get_price = AsyncMock(return_value=fresh_tick)
        mock_mt5.get_historical_data = AsyncMock(return_value=sample_ohlcv)

        report = await service._generate_quality_report("V10")

        assert report.symbol == "V10"
        assert report.quality in [DataQuality.EXCELLENT, DataQuality.GOOD, DataQuality.ACCEPTABLE]
        assert 0.0 <= report.score <= 1.0
        assert isinstance(report.issues, list)

        print(f"  PASSED: Quality report generated (quality={report.quality.value}, score={report.score})")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 5: Statistics tracking
    print("\n[Test 5] Statistics tracking...")
    try:
        stats = service.get_statistics()

        assert stats is not None
        assert hasattr(stats, "symbols_ingested")
        assert hasattr(stats, "total_ohlcv_records")
        assert hasattr(stats, "total_tick_records")
        assert hasattr(stats, "duration_seconds")

        print("  PASSED: Statistics tracked correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 6: Quality reports retrieval
    print("\n[Test 6] Quality reports retrieval...")
    try:
        # First generate a quality report
        fresh_tick = TickData(
            symbol="V10",
            bid=10000.5,
            ask=10001.0,
            spread=0.5,
            time=datetime.now(timezone.utc),
            volume=100,
        )

        base_time = datetime.now(timezone.utc)
        sample_ohlcv = [
            OHLCVData(
                symbol="V10",
                timestamp=base_time - timedelta(minutes=i),
                open=10000.0 + i,
                high=10005.0 + i,
                low=9995.0 + i,
                close=10002.0 + i,
                volume=100 + i,
            )
            for i in range(10, 0, -1)
        ]

        # Update the mock on the service's mt5_service
        service.mt5_service.get_price = AsyncMock(return_value=fresh_tick)
        service.mt5_service.get_historical_data = AsyncMock(return_value=sample_ohlcv)

        # Generate report - _generate_quality_report returns a report but doesn't store it
        # The storage happens in _quality_monitoring_loop. For this test, we'll manually store it.
        report = await service._generate_quality_report("V10")
        service._quality_reports["V10"] = report  # Manually store for testing

        # Now get quality reports - it should contain V10
        reports = service.get_quality_reports()

        assert isinstance(reports, dict)
        assert "V10" in reports, f"Expected 'V10' in reports, got: {list(reports.keys())}"
        assert reports["V10"].quality in [DataQuality.EXCELLENT, DataQuality.GOOD, DataQuality.ACCEPTABLE]

        print("  PASSED: Quality reports retrieved correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1

    # Test 7: Invalid timeframe handling
    print("\n[Test 7] Invalid timeframe handling...")
    try:
        result = await service._fetch_ohlcv_data("V10", "INVALID", 10)
        assert result is None

        print("  PASSED: Invalid timeframe handled correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 8: Manual fetch for all symbols
    print("\n[Test 8] Manual fetch for all symbols...")
    try:
        mock_mt5.get_price = AsyncMock(return_value=fresh_tick)
        mock_mt5.get_historical_data = AsyncMock(return_value=sample_ohlcv)

        with patch.object(service, "_store_tick_data"), patch.object(
            service, "_store_ohlcv_data"
        ):
            results = await service.fetch_all_symbols_once()

            assert "V10" in results
            assert "V25" in results

        print("  PASSED: Manual fetch works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 9: Service start/stop (mocked loops)
    print("\n[Test 9] Service start/stop...")
    try:
        with patch.object(service, "_tick_ingestion_loop"), patch.object(
            service, "_ohlcv_ingestion_loop"
        ), patch.object(service, "_quality_monitoring_loop"), patch.object(
            service, "_retention_cleanup_loop"
        ):
            await service.start_continuous_ingestion()
            assert service.is_running is True

            await service.stop_continuous_ingestion()
            assert service.is_running is False

        print("  PASSED: Service start/stop works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Test 10: Data quality enum values
    print("\n[Test 10] Data quality enum...")
    try:
        assert DataQuality.EXCELLENT.value == "excellent"
        assert DataQuality.GOOD.value == "good"
        assert DataQuality.ACCEPTABLE.value == "acceptable"
        assert DataQuality.POOR.value == "poor"
        assert DataQuality.BAD.value == "bad"

        print("  PASSED: Data quality enum values correct")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Test Summary: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)

    return tests_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_basic_tests())
    sys.exit(0 if success else 1)
