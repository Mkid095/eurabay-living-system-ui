"""
Test suite for backup scheduler.
Tests automated backup scheduling and execution.
"""
import pytest
from datetime import time, datetime
from unittest.mock import Mock, patch

from storage.backup_scheduler import BackupScheduler
from storage.backup_service import BackupService, BackupInfo


@pytest.fixture
def mock_backup_service():
    """Create a mock BackupService."""
    service = Mock(spec=BackupService)
    service.backup_database.return_value = BackupInfo(
        filename="test.db.gz",
        filepath="/tmp/test.db.gz",
        size_bytes=1024,
        size_human="1.00 KB",
        created_at=datetime.now(),
        is_compressed=True
    )
    service.get_backup_statistics.return_value = {
        "total_backups": 1,
        "total_size_bytes": 1024,
        "total_size_human": "1.00 KB"
    }
    return service


class TestBackupSchedulerInitialization:
    """Tests for BackupScheduler initialization."""

    def test_initialization_default(self):
        """Test scheduler initialization with defaults."""
        scheduler = BackupScheduler()

        assert scheduler.backup_time == time(3, 0)  # 3 AM
        assert scheduler.enabled is True
        assert scheduler.is_running() is False

    def test_initialization_custom(self, mock_backup_service):
        """Test scheduler initialization with custom settings."""
        custom_time = time(5, 30)
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            backup_time=custom_time,
            enabled=False
        )

        assert scheduler.backup_time == custom_time
        assert scheduler.enabled is False
        assert scheduler.backup_service == mock_backup_service

    def test_singleton_pattern(self):
        """Test that get_scheduler returns singleton instance."""
        scheduler1 = BackupScheduler.get_scheduler()
        scheduler2 = BackupScheduler.get_scheduler()

        assert scheduler1 is scheduler2


class TestSchedulerControl:
    """Tests for scheduler start/stop control."""

    @pytest.mark.asyncio
    async def test_start_scheduler(self, mock_backup_service):
        """Test starting the scheduler."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=True
        )

        await scheduler.start()

        assert scheduler.is_running() is True
        assert scheduler._task is not None

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_scheduler_disabled(self, mock_backup_service):
        """Test that disabled scheduler doesn't start."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=False
        )

        await scheduler.start()

        assert scheduler.is_running() is False

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, mock_backup_service):
        """Test stopping the scheduler."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=True
        )

        await scheduler.start()
        assert scheduler.is_running() is True

        await scheduler.stop()
        assert scheduler.is_running() is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, mock_backup_service):
        """Test starting an already running scheduler."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=True
        )

        await scheduler.start()
        await scheduler.start()  # Should not error

        await scheduler.stop()


class TestManualBackup:
    """Tests for manual backup execution."""

    @pytest.mark.asyncio
    async def test_run_once(self, mock_backup_service):
        """Test running a backup immediately."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=False
        )

        await scheduler.run_once()

        # Verify backup was called
        mock_backup_service.backup_database.assert_called_once()


class TestGetNextBackupTime:
    """Tests for getting next backup time."""

    def test_get_next_backup_time_when_running(self, mock_backup_service):
        """Test getting next backup time when scheduler is running."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            backup_time=time(3, 0),
            enabled=True
        )

        # Mock the running state
        scheduler._running = True

        next_time = scheduler.get_next_backup_time()

        assert next_time is not None
        # Should be a valid ISO format string
        datetime.fromisoformat(next_time)

    def test_get_next_backup_time_when_not_running(self, mock_backup_service):
        """Test getting next backup time when scheduler is not running."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=False
        )

        next_time = scheduler.get_next_backup_time()

        assert next_time is None

    def test_get_next_backup_time_when_disabled(self, mock_backup_service):
        """Test getting next backup time when scheduler is disabled."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=True,
            backup_time=time(3, 0)
        )

        # Don't start, so enabled but not running
        next_time = scheduler.get_next_backup_time()

        assert next_time is None


class TestIsRunning:
    """Tests for is_running method."""

    def test_is_running_when_running(self, mock_backup_service):
        """Test is_running returns True when running."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=True
        )

        # Manually set running state for testing
        scheduler._running = True

        assert scheduler.is_running() is True

    def test_is_running_when_not_running(self, mock_backup_service):
        """Test is_running returns False when not running."""
        scheduler = BackupScheduler(
            backup_service=mock_backup_service,
            enabled=True
        )

        assert scheduler.is_running() is False
