"""
Test suite for database backup and restore service.
Tests backup creation, restoration, listing, compression, and cleanup.
"""
import os
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pytest

from storage.backup_service import BackupService, BackupInfo, format_bytes


@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database for testing."""
    temp_dir = tempfile.mkdtemp()
    path = os.path.join(temp_dir, "trading.db")

    # Create a simple test database with some data
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create a test table
    cursor.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert test data
    test_data = [
        (1, "Test 1", 100.5),
        (2, "Test 2", 200.7),
        (3, "Test 3", 300.9),
    ]
    cursor.executemany("INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)", test_data)

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def backup_service(temp_db_path, temp_backup_dir):
    """Create a BackupService instance with test paths."""
    return BackupService(
        database_path=temp_db_path,
        backup_dir=temp_backup_dir,
        max_backups=10,  # Keep high for testing to avoid cleanup during tests
        compress=True
    )


class TestBackupServiceInitialization:
    """Tests for BackupService initialization."""

    def test_initialization(self, temp_db_path, temp_backup_dir):
        """Test BackupService initializes correctly."""
        service = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            max_backups=5,
            compress=False
        )

        assert service.database_path == Path(temp_db_path)
        assert service.backup_dir == Path(temp_backup_dir)
        assert service.max_backups == 5
        assert service.compress is False
        assert service.backup_dir.exists()

    def test_backup_dir_creation(self, temp_db_path):
        """Test that backup directory is created if it doesn't exist."""
        temp_dir = tempfile.mkdtemp()
        non_existent_dir = os.path.join(temp_dir, "backups")

        service = BackupService(
            database_path=temp_db_path,
            backup_dir=non_existent_dir
        )

        assert os.path.exists(non_existent_dir)

        # Cleanup
        shutil.rmtree(temp_dir)


class TestFormatBytes:
    """Tests for format_bytes utility function."""

    def test_format_bytes_small(self):
        """Test formatting small byte values."""
        assert format_bytes(500) == "500.00 B"

    def test_format_bytes_kilobytes(self):
        """Test formatting kilobyte values."""
        assert format_bytes(2048) == "2.00 KB"

    def test_format_bytes_megabytes(self):
        """Test formatting megabyte values."""
        assert format_bytes(3 * 1024 * 1024) == "3.00 MB"

    def test_format_bytes_gigabytes(self):
        """Test formatting gigabyte values."""
        assert format_bytes(5 * 1024 * 1024 * 1024) == "5.00 GB"


class TestBackupCreation:
    """Tests for backup creation functionality."""

    def test_backup_database_creates_file(self, backup_service):
        """Test that backup_database creates a backup file."""
        backup_info = backup_service.backup_database()

        assert os.path.exists(backup_info.filepath)
        assert backup_info.is_compressed is True
        assert ".gz" in backup_info.filename

    def test_backup_filename_format(self, backup_service):
        """Test that backup filename follows expected format."""
        backup_info = backup_service.backup_database()

        # Filename should be: {db_name}_{timestamp_with_microseconds}.db.gz
        assert backup_info.filename.startswith("trading_")
        assert backup_info.filename.endswith(".db.gz")
        # Should have microseconds in timestamp
        parts = backup_info.filename.replace(".db.gz", "").split("_")
        assert len(parts) >= 3  # trading, date, time_with_microseconds

    def test_backup_info_fields(self, backup_service):
        """Test that BackupInfo contains all required fields."""
        backup_info = backup_service.backup_database()

        assert backup_info.filename is not None
        assert backup_info.filepath is not None
        assert backup_info.size_bytes > 0
        assert backup_info.size_human is not None
        assert backup_info.created_at is not None
        assert isinstance(backup_info.created_at, datetime)

    def test_backup_uncompressed(self, temp_db_path, temp_backup_dir):
        """Test creating uncompressed backups."""
        service = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            compress=False
        )

        backup_info = service.backup_database()

        assert backup_info.is_compressed is False
        assert not backup_info.filename.endswith(".gz")
        assert os.path.exists(backup_info.filepath)

    def test_backup_nonexistent_database(self, temp_backup_dir):
        """Test that backup fails for non-existent database."""
        service = BackupService(
            database_path="/nonexistent/path/to/database.db",
            backup_dir=temp_backup_dir
        )

        with pytest.raises(FileNotFoundError):
            service.backup_database()


class TestRestoreDatabase:
    """Tests for database restoration functionality."""

    def test_restore_database(self, backup_service, temp_db_path):
        """Test restoring database from backup."""
        # Create backup
        backup_info = backup_service.backup_database()

        # Modify database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('Modified', 999.9)")
        conn.commit()
        conn.close()

        # Restore from backup
        backup_service.restore_database(backup_info.filename)

        # Verify restoration
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()

        # Should have original 3 rows, not 4
        assert count == 3

    def test_restore_nonexistent_backup(self, backup_service):
        """Test that restore fails for non-existent backup."""
        with pytest.raises(FileNotFoundError):
            backup_service.restore_database("nonexistent_backup.db.gz")

    def test_restore_creates_pre_restore_backup(self, backup_service, temp_db_path):
        """Test that restore creates a pre-restore backup."""
        # Create initial backup
        backup_info = backup_service.backup_database()

        # Modify database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('Test', 123.4)")
        conn.commit()
        conn.close()

        # Restore
        backup_service.restore_database(backup_info.filename)

        # Check for pre-restore backup
        backups = backup_service.list_backups()
        pre_restore_backups = [b for b in backups if "pre_restore" in b.filename]

        assert len(pre_restore_backups) >= 1


class TestListBackups:
    """Tests for listing backups."""

    def test_list_backups_empty(self, backup_service):
        """Test listing backups when none exist."""
        backups = backup_service.list_backups()
        assert len(backups) == 0

    def test_list_backups_multiple(self, temp_db_path):
        """Test listing multiple backups."""
        # Use a fresh temp dir for this test
        temp_dir = tempfile.mkdtemp()
        try:
            service = BackupService(
                database_path=temp_db_path,
                backup_dir=temp_dir,
                max_backups=10,
                compress=True
            )

            # Create 3 backups
            for _ in range(3):
                service.backup_database()

            backups = service.list_backups()
            assert len(backups) == 3

            # Should be sorted newest first
            assert backups[0].created_at >= backups[1].created_at
            assert backups[1].created_at >= backups[2].created_at
        finally:
            shutil.rmtree(temp_dir)

    def test_list_backups_mixed_compression(self, temp_db_path, temp_backup_dir):
        """Test listing backups with mixed compression."""
        # Create compressed backup
        service_compressed = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            compress=True
        )
        service_compressed.backup_database()

        # Create uncompressed backup
        service_uncompressed = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            compress=False
        )
        service_uncompressed.backup_database()

        service = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir
        )

        backups = service.list_backups()
        assert len(backups) == 2

        compressed = [b for b in backups if b.is_compressed]
        uncompressed = [b for b in backups if not b.is_compressed]

        assert len(compressed) == 1
        assert len(uncompressed) == 1


class TestCleanupOldBackups:
    """Tests for automatic cleanup of old backups."""

    def test_cleanup_keeps_max_backups(self, temp_db_path, temp_backup_dir):
        """Test that cleanup keeps only max_backups most recent."""
        # Create service with low max_backups
        service = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            max_backups=3,  # Keep only 3
            compress=True
        )

        # Create 5 backups (max is 3)
        for i in range(5):
            service.backup_database()

        backups = service.list_backups()

        # Should have exactly 3 backups
        assert len(backups) == 3

    def test_cleanup_removes_oldest(self, temp_db_path, temp_backup_dir):
        """Test that cleanup removes oldest backups."""
        # Create service with low max_backups
        service = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            max_backups=3,  # Keep only 3
            compress=True
        )

        # Create 5 backups
        backup_filenames = []
        for i in range(5):
            info = service.backup_database()
            backup_filenames.append(info.filename)

        # Get current backups
        current_backups = service.list_backups()
        current_filenames = [b.filename for b in current_backups]

        # Oldest 2 should be removed
        assert backup_filenames[0] not in current_filenames
        assert backup_filenames[1] not in current_filenames

        # Newest 3 should remain
        assert backup_filenames[2] in current_filenames
        assert backup_filenames[3] in current_filenames
        assert backup_filenames[4] in current_filenames


class TestBackupStatistics:
    """Tests for backup statistics functionality."""

    def test_backup_statistics_empty(self, backup_service):
        """Test statistics when no backups exist."""
        stats = backup_service.get_backup_statistics()

        assert stats["total_backups"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["compressed_count"] == 0
        assert stats["uncompressed_count"] == 0
        assert stats["newest_backup"] is None
        assert stats["oldest_backup"] is None

    def test_backup_statistics_with_data(self, backup_service):
        """Test statistics with backups present."""
        # Create 2 backups
        backup1 = backup_service.backup_database()
        backup2 = backup_service.backup_database()

        stats = backup_service.get_backup_statistics()

        # Should have at least 2 backups (may have pre-restore backups from other tests)
        assert stats["total_backups"] >= 2
        assert stats["total_size_bytes"] > 0
        assert stats["compressed_count"] >= 2
        assert stats["newest_backup"] is not None
        assert stats["oldest_backup"] is not None


class TestDeleteBackup:
    """Tests for deleting individual backups."""

    def test_delete_backup(self, backup_service):
        """Test deleting a specific backup."""
        # Create backup
        backup_info = backup_service.backup_database()

        # Delete it
        result = backup_service.delete_backup(backup_info.filename)

        assert result is True
        assert not os.path.exists(backup_info.filepath)

    def test_delete_nonexistent_backup(self, backup_service):
        """Test deleting non-existent backup."""
        result = backup_service.delete_backup("nonexistent.db.gz")
        assert result is False


class TestVerifyBackup:
    """Tests for backup verification functionality."""

    def test_verify_compressed_backup(self, backup_service):
        """Test verifying a compressed backup."""
        backup_info = backup_service.backup_database()

        result = backup_service.verify_backup(backup_info.filename)

        assert result is True

    def test_verify_uncompressed_backup(self, temp_db_path, temp_backup_dir):
        """Test verifying an uncompressed backup."""
        service = BackupService(
            database_path=temp_db_path,
            backup_dir=temp_backup_dir,
            compress=False
        )

        backup_info = service.backup_database()
        result = service.verify_backup(backup_info.filename)

        assert result is True

    def test_verify_nonexistent_backup(self, backup_service):
        """Test verifying non-existent backup."""
        result = backup_service.verify_backup("nonexistent.db.gz")

        assert result is False


class TestIntegration:
    """Integration tests for backup workflows."""

    def test_full_backup_restore_cycle(self, backup_service, temp_db_path):
        """Test complete backup and restore cycle."""
        # Create initial backup
        backup_info = backup_service.backup_database()

        # Modify database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('New', 111.1)")
        conn.commit()
        conn.close()

        # Verify modification
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count_before_restore = cursor.fetchone()[0]
        conn.close()

        assert count_before_restore == 4

        # Restore
        backup_service.restore_database(backup_info.filename)

        # Verify restoration
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count_after_restore = cursor.fetchone()[0]
        conn.close()

        assert count_after_restore == 3

    def test_multiple_backups_and_restore_middle(self, temp_db_path):
        """Test creating multiple backups and restoring from middle one."""
        # Use a fresh temp dir for this test to avoid conflicts
        temp_dir = tempfile.mkdtemp()
        try:
            service = BackupService(
                database_path=temp_db_path,
                backup_dir=temp_dir,
                max_backups=10,
                compress=True
            )

            # Create 3 backups with different states
            backup1 = service.backup_database()

            # Modify database
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_table (name, value) VALUES ('V2', 222.2)")
            conn.commit()
            conn.close()

            backup2 = service.backup_database()

            # Modify again
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_table (name, value) VALUES ('V3', 333.3)")
            conn.commit()
            conn.close()

            backup3 = service.backup_database()

            # Restore from middle backup
            service.restore_database(backup2.filename)

            # Verify we have the middle state (4 rows: 3 original + 1 added)
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 4
        finally:
            shutil.rmtree(temp_dir)
