"""
Test suite for DataRetentionService and CleanupScheduler.

Tests all cleanup operations including market data, logs, and compression.
"""

import asyncio
import tempfile
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import SystemLog, Base
from storage import DataRetentionService, CleanupScheduler, CleanupResult


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
async def temp_storage_dir():
    """Create a temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
async def test_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def sample_market_data():
    """Create sample market data DataFrame."""
    now = datetime.now()
    dates = [
        now - timedelta(days=100),  # Old - should be cleaned
        now - timedelta(days=60),   # Old - should be cleaned
        now - timedelta(days=30),   # Within retention
        now - timedelta(days=7),    # Recent
        now,                        # Current
    ]

    return pd.DataFrame({
        "timestamp": dates,
        "open": [1.1000, 1.1050, 1.1100, 1.1150, 1.1200],
        "high": [1.1050, 1.1100, 1.1150, 1.1200, 1.1250],
        "low": [1.0950, 1.1000, 1.1050, 1.1100, 1.1150],
        "close": [1.1025, 1.1075, 1.1125, 1.1175, 1.1225],
        "volume": [1000, 1100, 1200, 1300, 1400],
    })


@pytest.fixture
async def populate_test_logs(test_session):
    """Populate test database with sample log entries."""
    now = datetime.now()

    logs = [
        SystemLog(
            timestamp=now - timedelta(days=60),
            level="INFO",
            message="Old log entry 1",
            source="test",
        ),
        SystemLog(
            timestamp=now - timedelta(days=40),
            level="WARNING",
            message="Old log entry 2",
            source="test",
        ),
        SystemLog(
            timestamp=now - timedelta(days=20),
            level="ERROR",
            message="Recent log entry",
            source="test",
        ),
        SystemLog(
            timestamp=now - timedelta(days=5),
            level="INFO",
            message="Very recent log",
            source="test",
        ),
    ]

    for log in logs:
        test_session.add(log)

    await test_session.commit()

    return logs


# ============================================================================
# DataRetentionService Tests
# ============================================================================

@pytest.mark.asyncio
async def test_data_retention_service_initialization(test_session, temp_storage_dir):
    """Test DataRetentionService initialization."""
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
        market_retention_days=90,
        log_retention_days=30,
    )

    assert service.market_retention_days == 90
    assert service.log_retention_days == 30
    assert service.session is not None


@pytest.mark.asyncio
async def test_cleanup_old_market_data_dry_run(
    test_session,
    temp_storage_dir,
    sample_market_data,
):
    """Test market data cleanup in dry-run mode."""
    # Save test data
    from storage import TimeSeriesStorage
    storage = TimeSeriesStorage(base_path=temp_storage_dir)
    storage.save_market_data(sample_market_data, "EURUSD", append_mode=False)

    # Run cleanup in dry-run mode
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
        market_retention_days=45,  # Should clean up data older than 45 days
    )

    result = await service.cleanup_old_market_data(dry_run=True)

    assert result.operation == "cleanup_old_market_data"
    assert result.dry_run is True
    assert result.files_deleted >= 1  # At least one old file


@pytest.mark.asyncio
async def test_cleanup_old_market_data_actual(
    test_session,
    temp_storage_dir,
    sample_market_data,
):
    """Test actual market data cleanup."""
    # Save test data
    from storage import TimeSeriesStorage
    storage = TimeSeriesStorage(base_path=temp_storage_dir)
    storage.save_market_data(sample_market_data, "EURUSD", append_mode=False)

    # Run actual cleanup
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
        market_retention_days=45,  # Should clean up data older than 45 days
    )

    # First run dry-run to see what would be deleted
    dry_result = await service.cleanup_old_market_data(dry_run=True)
    expected_deletions = dry_result.files_deleted

    # Run actual cleanup
    result = await service.cleanup_old_market_data(dry_run=False)

    assert result.operation == "cleanup_old_market_data"
    assert result.dry_run is False
    assert result.files_deleted == expected_deletions
    assert result.bytes_freed > 0

    # Verify old files were deleted
    remaining_files = list(Path(temp_storage_dir).rglob("*.parquet"))
    assert len(remaining_files) >= 2  # At least recent files remain


@pytest.mark.asyncio
async def test_cleanup_old_logs_dry_run(test_session, populate_test_logs):
    """Test log cleanup in dry-run mode."""
    service = DataRetentionService(
        session=test_session,
        log_retention_days=30,  # Should clean up logs older than 30 days
    )

    result = await service.cleanup_old_logs(dry_run=True)

    assert result.operation == "cleanup_old_logs"
    assert result.dry_run is True
    assert result.records_deleted >= 1  # At least one old log


@pytest.mark.asyncio
async def test_cleanup_old_logs_actual(test_session, populate_test_logs):
    """Test actual log cleanup."""
    service = DataRetentionService(
        session=test_session,
        log_retention_days=30,  # Should clean up logs older than 30 days
    )

    # Run actual cleanup
    result = await service.cleanup_old_logs(dry_run=False)

    assert result.operation == "cleanup_old_logs"
    assert result.dry_run is False
    assert result.records_deleted >= 1  # At least one old log deleted

    # Verify old logs were deleted
    from sqlalchemy import select
    query = select(SystemLog).where(
        SystemLog.timestamp < datetime.now() - timedelta(days=30)
    )
    result_check = await test_session.execute(query)
    remaining_old_logs = result_check.scalars().all()

    assert len(remaining_old_logs) == 0  # All old logs should be deleted


@pytest.mark.asyncio
async def test_compress_old_files_dry_run(temp_storage_dir):
    """Test file compression in dry-run mode."""
    # Create test log files
    logs_dir = Path(temp_storage_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    old_log = logs_dir / "old.log"
    old_log.write_text("Old log content\n" * 100)

    recent_log = logs_dir / "recent.log"
    recent_log.write_text("Recent log content\n" * 100)

    # Update modification time for old file
    old_time = datetime.now() - timedelta(days=10)
    import os
    os.utime(old_log, (old_time.timestamp(), old_time.timestamp()))

    service = DataRetentionService(
        session=None,
        compress_days=7,  # Should compress files older than 7 days
    )

    result = await service.compress_old_files(dry_run=True)

    assert result.operation == "compress_old_files"
    assert result.dry_run is True
    assert result.files_compressed >= 1  # At least one file compressed


@pytest.mark.asyncio
async def test_run_full_cleanup(
    test_session,
    temp_storage_dir,
    sample_market_data,
    populate_test_logs,
):
    """Test running full cleanup (all operations)."""
    # Save test data
    from storage import TimeSeriesStorage
    storage = TimeSeriesStorage(base_path=temp_storage_dir)
    storage.save_market_data(sample_market_data, "EURUSD", append_mode=False)

    # Create test log files
    logs_dir = Path(temp_storage_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    old_log = logs_dir / "old.log"
    old_log.write_text("Old log content\n" * 100)

    old_time = datetime.now() - timedelta(days=10)
    import os
    os.utime(old_log, (old_time.timestamp(), old_time.timestamp()))

    # Run full cleanup
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
        market_retention_days=45,
        log_retention_days=30,
        compress_days=7,
    )

    results = await service.run_full_cleanup(dry_run=True)

    assert "market_data" in results
    assert "logs" in results
    assert "compression" in results

    # All results should be CleanupResult objects
    for key, result in results.items():
        assert isinstance(result, CleanupResult)
        assert result.dry_run is True


@pytest.mark.asyncio
async def test_get_retention_config(test_session, temp_storage_dir):
    """Test getting retention configuration."""
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
        market_retention_days=90,
        log_retention_days=30,
        compress_days=7,
    )

    config = service.get_retention_config()

    assert config["market_data_retention_days"] == 90
    assert config["log_retention_days"] == 30
    assert config["compress_after_days"] == 7
    assert "cutoff_dates" in config


@pytest.mark.asyncio
async def test_get_cleanup_statistics(
    test_session,
    temp_storage_dir,
    sample_market_data,
    populate_test_logs,
):
    """Test getting cleanup statistics."""
    # Save test data
    from storage import TimeSeriesStorage
    storage = TimeSeriesStorage(base_path=temp_storage_dir)
    storage.save_market_data(sample_market_data, "EURUSD", append_mode=False)

    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
        market_retention_days=45,
        log_retention_days=30,
    )

    stats = await service.get_cleanup_statistics()

    assert "market_data" in stats
    assert "logs" in stats
    assert "potential_cleanup" in stats

    assert stats["market_data"]["current_size_bytes"] >= 0
    assert stats["logs"]["old_records_count"] >= 0


# ============================================================================
# CleanupScheduler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_scheduler_initialization(test_engine):
    """Test CleanupScheduler initialization."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    scheduler = CleanupScheduler(
        session_factory=session_factory,
        cleanup_time=datetime(2024, 1, 1, 2, 0).time(),
    )

    assert scheduler.cleanup_time.hour == 2
    assert scheduler.cleanup_time.minute == 0
    assert scheduler.is_running() is False


@pytest.mark.asyncio
async def test_scheduler_start_stop(test_engine):
    """Test starting and stopping the scheduler."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    scheduler = CleanupScheduler(
        session_factory=session_factory,
    )

    # Start scheduler
    await scheduler.start()
    assert scheduler.is_running() is True

    # Stop scheduler
    await scheduler.stop()
    assert scheduler.is_running() is False


@pytest.mark.asyncio
async def test_scheduler_run_once(
    test_engine,
    temp_storage_dir,
    sample_market_data,
):
    """Test running cleanup once manually."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Add SystemLog to database if not exists
    async with session_factory() as session:
        log = SystemLog(
            timestamp=datetime.now() - timedelta(days=60),
            level="INFO",
            message="Test log",
            source="test",
        )
        session.add(log)
        await session.commit()

    scheduler = CleanupScheduler(
        session_factory=session_factory,
        market_data_path=temp_storage_dir,
    )

    # This should complete without errors
    await scheduler.run_once()


@pytest.mark.asyncio
async def test_get_scheduler_singleton(test_engine):
    """Test get_scheduler returns singleton instance."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    scheduler1 = get_scheduler(session_factory=session_factory)
    scheduler2 = get_scheduler(session_factory=session_factory)

    assert scheduler1 is scheduler2  # Same instance


# ============================================================================
# Utility Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_result_dataclass():
    """Test CleanupResult dataclass."""
    result = CleanupResult(
        operation="test_operation",
        files_deleted=5,
        bytes_freed=1024,
        records_deleted=10,
        duration_seconds=1.5,
        dry_run=False,
        details={"test": "data"},
    )

    assert result.operation == "test_operation"
    assert result.files_deleted == 5
    assert result.bytes_freed == 1024
    assert result.records_deleted == 10
    assert result.duration_seconds == 1.5
    assert result.dry_run is False
    assert result.details == {"test": "data"}


@pytest.mark.asyncio
async def test_directory_size_calculation(test_session, temp_storage_dir):
    """Test directory size calculation."""
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
    )

    # Create test files
    test_file = Path(temp_storage_dir) / "test.txt"
    test_file.write_text("x" * 1024)  # 1 KB file

    size = service._get_directory_size(Path(temp_storage_dir))

    assert size >= 1024  # At least 1 KB


@pytest.mark.asyncio
async def test_format_bytes(test_session, temp_storage_dir):
    """Test byte formatting utility."""
    service = DataRetentionService(
        session=test_session,
        market_data_path=temp_storage_dir,
    )

    assert service._format_bytes(500) == "500.00 B"
    assert service._format_bytes(1024) == "1.00 KB"
    assert service._format_bytes(1024 * 1024) == "1.00 MB"
    assert service._format_bytes(1024 * 1024 * 1024) == "1.00 GB"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
