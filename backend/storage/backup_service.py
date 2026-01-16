"""
Database backup and restore service for EURABAY Living System.
Provides automated backup creation, restoration, listing, and cleanup.
"""
import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from loguru import logger

from app.core.config import settings


@dataclass
class BackupInfo:
    """Information about a backup file."""
    filename: str
    filepath: str
    size_bytes: int
    size_human: str
    created_at: datetime
    is_compressed: bool


def format_bytes(size_bytes: int) -> str:
    """
    Format bytes to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


class BackupService:
    """
    Service for database backup and restore operations.
    Supports compression, automatic cleanup, and scheduled backups.
    """

    def __init__(
        self,
        database_path: Optional[str] = None,
        backup_dir: Optional[str] = None,
        max_backups: int = 7,
        compress: bool = True
    ):
        """
        Initialize backup service.

        Args:
            database_path: Path to SQLite database file
            backup_dir: Directory to store backups
            max_backups: Maximum number of backups to keep
            compress: Whether to compress backups with gzip
        """
        self.database_path = Path(database_path or settings.DATABASE_PATH)
        self.backup_dir = Path(backup_dir or "backend/backups")
        self.max_backups = max_backups
        self.compress = compress

        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"BackupService initialized: database={self.database_path}, "
            f"backup_dir={self.backup_dir}, max_backups={max_backups}, "
            f"compress={compress}"
        )

    def backup_database(self) -> BackupInfo:
        """
        Create a backup of the database.

        Returns:
            BackupInfo with details about the created backup

        Raises:
            FileNotFoundError: If database file doesn't exist
            IOError: If backup cannot be created
        """
        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Database file not found: {self.database_path}"
            )

        # Generate timestamped filename with microseconds for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        db_name = self.database_path.stem

        if self.compress:
            backup_filename = f"{db_name}_{timestamp}.db.gz"
        else:
            backup_filename = f"{db_name}_{timestamp}.db"

        backup_path = self.backup_dir / backup_filename

        logger.info(f"Creating database backup: {backup_filename}")

        try:
            if self.compress:
                # Compress while copying
                with open(self.database_path, "rb") as f_in:
                    with gzip.open(backup_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Simple copy
                shutil.copy2(self.database_path, backup_path)

            # Get file size
            size_bytes = backup_path.stat().st_size

            backup_info = BackupInfo(
                filename=backup_filename,
                filepath=str(backup_path),
                size_bytes=size_bytes,
                size_human=format_bytes(size_bytes),
                created_at=datetime.now(),
                is_compressed=self.compress
            )

            logger.success(
                f"Backup created successfully: {backup_filename} "
                f"({backup_info.size_human})"
            )

            # Clean up old backups
            self._cleanup_old_backups()

            return backup_info

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise IOError(f"Backup creation failed: {e}") from e

    def restore_database(self, backup_filename: str) -> None:
        """
        Restore database from a backup.

        Args:
            backup_filename: Name of the backup file to restore

        Raises:
            FileNotFoundError: If backup file doesn't exist
            IOError: If restore fails
        """
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(
                f"Backup file not found: {backup_filename}"
            )

        logger.info(f"Restoring database from: {backup_filename}")

        try:
            # Create timestamped backup of current database before restoring
            if self.database_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_restore_backup = (
                    self.backup_dir /
                    f"{self.database_path.stem}_pre_restore_{timestamp}.db"
                )
                shutil.copy2(self.database_path, pre_restore_backup)
                logger.info(f"Pre-restore backup created: {pre_restore_backup.name}")

            # Restore from backup
            if backup_filename.endswith(".gz"):
                # Decompress and restore
                with gzip.open(backup_path, "rb") as f_in:
                    with open(self.database_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Simple copy
                shutil.copy2(backup_path, self.database_path)

            logger.success(
                f"Database restored successfully from: {backup_filename}"
            )

        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            raise IOError(f"Database restore failed: {e}") from e

    def list_backups(self) -> List[BackupInfo]:
        """
        List all available backups.

        Returns:
            List of BackupInfo objects, sorted by creation time (newest first)
        """
        backups = []

        for filepath in self.backup_dir.glob("*.db*"):
            try:
                stat = filepath.stat()
                created_at = datetime.fromtimestamp(stat.st_ctime)
                size_bytes = stat.st_size

                backup_info = BackupInfo(
                    filename=filepath.name,
                    filepath=str(filepath),
                    size_bytes=size_bytes,
                    size_human=format_bytes(size_bytes),
                    created_at=created_at,
                    is_compressed=filepath.suffix == ".gz"
                )
                backups.append(backup_info)

            except Exception as e:
                logger.warning(f"Failed to read backup info for {filepath.name}: {e}")

        # Sort by creation time, newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)

        return backups

    def _cleanup_old_backups(self) -> None:
        """
        Remove old backups, keeping only the most recent max_backups.
        """
        backups = self.list_backups()

        if len(backups) <= self.max_backups:
            logger.debug(f"Total backups ({len(backups)}) within limit ({self.max_backups})")
            return

        # Remove oldest backups
        to_delete = backups[self.max_backups:]
        deleted_files = []

        for backup in to_delete:
            try:
                os.remove(backup.filepath)
                deleted_files.append(backup.filename)
                logger.info(f"Deleted old backup: {backup.filename}")
            except Exception as e:
                logger.error(f"Failed to delete backup {backup.filename}: {e}")

        if deleted_files:
            logger.info(
                f"Cleaned up {len(deleted_files)} old backup(s), "
                f"keeping {self.max_backups} most recent"
            )

    def get_backup_statistics(self) -> dict:
        """
        Get statistics about backups.

        Returns:
            Dictionary with backup statistics
        """
        backups = self.list_backups()

        total_size = sum(b.size_bytes for b in backups)
        compressed_count = sum(1 for b in backups if b.is_compressed)

        newest = backups[0] if backups else None
        oldest = backups[-1] if backups else None

        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size,
            "total_size_human": format_bytes(total_size),
            "compressed_count": compressed_count,
            "uncompressed_count": len(backups) - compressed_count,
            "newest_backup": newest.filename if newest else None,
            "oldest_backup": oldest.filename if oldest else None,
            "newest_date": newest.created_at.isoformat() if newest else None,
            "oldest_date": oldest.created_at.isoformat() if oldest else None,
            "backup_dir": str(self.backup_dir),
            "database_path": str(self.database_path),
            "max_backups": self.max_backups
        }

    def delete_backup(self, backup_filename: str) -> bool:
        """
        Delete a specific backup file.

        Args:
            backup_filename: Name of the backup file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            logger.warning(f"Backup file not found: {backup_filename}")
            return False

        try:
            os.remove(backup_path)
            logger.info(f"Deleted backup: {backup_filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_filename}: {e}")
            return False

    def verify_backup(self, backup_filename: str) -> bool:
        """
        Verify that a backup file is valid and readable.

        Args:
            backup_filename: Name of the backup file to verify

        Returns:
            True if backup is valid, False otherwise
        """
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            logger.warning(f"Backup file not found: {backup_filename}")
            return False

        try:
            # For compressed backups, verify we can read the gzip header
            if backup_filename.endswith(".gz"):
                with gzip.open(backup_path, "rb") as f:
                    # Read first 1024 bytes to verify it's a valid gzip file
                    f.read(1024)
            else:
                # For uncompressed backups, verify we can read the SQLite header
                with open(backup_path, "rb") as f:
                    header = f.read(16)
                    if not header.startswith(b"SQLite format 3\000"):
                        return False

            logger.info(f"Backup verified: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"Backup verification failed for {backup_filename}: {e}")
            return False
