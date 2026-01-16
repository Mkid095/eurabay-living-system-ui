"""
DataRetentionService - Automated data retention and cleanup for EURABAY Living System.

This module provides automated cleanup of old market data, logs, and compression
of files to manage disk space efficiently.
"""

import os
import gzip
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger

from app.models import SystemLog
from .time_series_storage import TimeSeriesStorage


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    operation: str
    files_deleted: int
    bytes_freed: int
    records_deleted: int
    duration_seconds: float
    dry_run: bool
    details: Dict[str, Any]


class DataRetentionService:
    """
    Service for managing data retention and cleanup operations.

    Features:
    - Cleanup old market data (Parquet files)
    - Cleanup old system logs from database
    - Compress old files
    - Scheduled cleanup operations
    - Dry-run mode for testing
    - Configurable retention periods
    - Disk space calculation
    - Comprehensive logging
    """

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        market_data_path: str = "backend/data/market",
        market_retention_days: int = 90,
        log_retention_days: int = 30,
        compress_days: int = 7,
    ):
        """
        Initialize DataRetentionService.

        Args:
            session: Async database session for log cleanup
            market_data_path: Path to market data storage
            market_retention_days: Days to keep market data (default: 90)
            log_retention_days: Days to keep logs (default: 30)
            compress_days: Age in days before compressing files (default: 7)
        """
        self.session = session
        self.market_data_path = Path(market_data_path)
        self.market_retention_days = market_retention_days
        self.log_retention_days = log_retention_days
        self.compress_days = compress_days

        # Initialize TimeSeriesStorage for market data operations
        self.time_series_storage = TimeSeriesStorage(base_path=market_data_path)

        logger.info(
            f"DataRetentionService initialized: market_retention={market_retention_days}d, "
            f"log_retention={log_retention_days}d, compress_after={compress_days}d"
        )

    def _get_directory_size(self, path: Path) -> int:
        """
        Calculate total size of a directory in bytes.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        total_size = 0
        if path.exists() and path.is_dir():
            for item in path.rglob("*"):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except OSError:
                        pass
        return total_size

    def _format_bytes(self, bytes_value: int) -> str:
        """
        Format bytes to human-readable string.

        Args:
            bytes_value: Size in bytes

        Returns:
            Formatted string (e.g., "1.23 GB")
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

    def _get_cutoff_date(self, days: int) -> date:
        """
        Get cutoff date for retention calculation.

        Args:
            days: Number of days to retain

        Returns:
            Cutoff date
        """
        return (datetime.now() - timedelta(days=days)).date()

    async def cleanup_old_market_data(
        self,
        dry_run: bool = False,
        symbol: Optional[str] = None,
    ) -> CleanupResult:
        """
        Cleanup old market data Parquet files older than retention period.

        Args:
            dry_run: If True, only report what would be deleted
            symbol: Specific symbol to clean (optional)

        Returns:
            CleanupResult with operation details
        """
        start_time = datetime.now()
        cutoff_date = self._get_cutoff_date(self.market_retention_days)

        logger.info(
            f"Starting market data cleanup (dry_run={dry_run}, "
            f"cutoff_date={cutoff_date}, retention={self.market_retention_days}d)"
        )

        # Calculate disk space before
        space_before = self._get_directory_size(self.market_data_path)

        files_deleted = 0
        bytes_freed = 0
        symbols_processed: List[str] = []

        # Get symbols to process
        symbols_to_process = (
            [symbol] if symbol else self.time_series_storage.get_available_symbols()
        )

        for sym in symbols_to_process:
            symbol_dir = self.market_data_path / sym

            if not symbol_dir.exists():
                continue

            # Find files older than cutoff date
            for file_path in symbol_dir.glob("*.parquet"):
                try:
                    # Extract date from filename (YYYY-MM-DD.parquet)
                    file_date = datetime.strptime(file_path.stem, "%Y-%m-%d").date()

                    if file_date < cutoff_date:
                        file_size = file_path.stat().st_size

                        if not dry_run:
                            # Delete the file
                            file_path.unlink()
                            logger.info(f"Deleted {file_path} ({self._format_bytes(file_size)})")

                        files_deleted += 1
                        bytes_freed += file_size
                        symbols_processed.append(sym)

                except (ValueError, OSError) as e:
                    logger.warning(f"Could not process {file_path}: {e}")

        # Update metadata if not dry run
        if not dry_run and symbols_processed:
            for sym in set(symbols_processed):
                self._update_metadata_after_cleanup(sym, cutoff_date)

        duration = (datetime.now() - start_time).total_seconds()

        result = CleanupResult(
            operation="cleanup_old_market_data",
            files_deleted=files_deleted,
            bytes_freed=bytes_freed,
            records_deleted=0,  # Parquet files don't track record count
            duration_seconds=duration,
            dry_run=dry_run,
            details={
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.market_retention_days,
                "symbols_processed": list(set(symbols_processed)),
                "space_before_mb": round(space_before / (1024 * 1024), 2),
                "space_after_mb": round(
                    (space_before - bytes_freed) / (1024 * 1024), 2
                ) if not dry_run else None,
                "bytes_freed_formatted": self._format_bytes(bytes_freed),
            },
        )

        logger.info(
            f"Market data cleanup complete: {files_deleted} files, "
            f"{self._format_bytes(bytes_freed)} freed, {duration:.2f}s"
        )

        return result

    async def cleanup_old_logs(
        self,
        dry_run: bool = False,
        log_level: Optional[str] = None,
    ) -> CleanupResult:
        """
        Cleanup old system logs from database older than retention period.

        Args:
            dry_run: If True, only report what would be deleted
            log_level: Specific log level to clean (optional)

        Returns:
            CleanupResult with operation details
        """
        start_time = datetime.now()
        cutoff_datetime = datetime.now() - timedelta(days=self.log_retention_days)

        logger.info(
            f"Starting log cleanup (dry_run={dry_run}, "
            f"cutoff={cutoff_datetime}, retention={self.log_retention_days}d)"
        )

        if not self.session:
            logger.error("No database session provided for log cleanup")
            return CleanupResult(
                operation="cleanup_old_logs",
                files_deleted=0,
                bytes_freed=0,
                records_deleted=0,
                duration_seconds=0,
                dry_run=dry_run,
                details={"error": "No database session provided"},
            )

        records_deleted = 0

        try:
            # Build query
            query = select(SystemLog).where(SystemLog.timestamp < cutoff_datetime)

            if log_level:
                query = query.where(SystemLog.level == log_level)

            # Get count first
            result = await self.session.execute(query)
            logs_to_delete = result.scalars().all()
            records_deleted = len(logs_to_delete)

            if not dry_run and records_deleted > 0:
                # Delete old logs
                delete_query = delete(SystemLog).where(
                    SystemLog.timestamp < cutoff_datetime
                )

                if log_level:
                    delete_query = delete_query.where(SystemLog.level == log_level)

                await self.session.execute(delete_query)
                await self.session.commit()

                logger.info(f"Deleted {records_deleted} log records")

        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
            await self.session.rollback()
            raise

        duration = (datetime.now() - start_time).total_seconds()

        result = CleanupResult(
            operation="cleanup_old_logs",
            files_deleted=0,
            bytes_freed=0,  # Database size reduction not calculated
            records_deleted=records_deleted,
            duration_seconds=duration,
            dry_run=dry_run,
            details={
                "cutoff_datetime": cutoff_datetime.isoformat(),
                "retention_days": self.log_retention_days,
                "log_level": log_level,
                "records_deleted": records_deleted,
            },
        )

        logger.info(
            f"Log cleanup complete: {records_deleted} records deleted, {duration:.2f}s"
        )

        return result

    async def compress_old_files(
        self,
        dry_run: bool = False,
        file_pattern: str = "*.log",
    ) -> CleanupResult:
        """
        Compress old log files that are older than compression threshold.

        Args:
            dry_run: If True, only report what would be compressed
            file_pattern: File pattern to match (default: "*.log")

        Returns:
            CleanupResult with operation details
        """
        start_time = datetime.now()
        cutoff_date = self._get_cutoff_date(self.compress_days)

        logger.info(
            f"Starting file compression (dry_run={dry_run}, "
            f"cutoff_date={cutoff_date}, compress_after={self.compress_days}d)"
        )

        files_compressed = 0
        bytes_saved = 0

        # Define directories to search for compressible files
        search_dirs = [
            Path("backend/logs"),
            Path("logs"),
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file_path in search_dir.rglob(file_pattern):
                try:
                    # Check file age
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    file_date = file_mtime.date()

                    # Skip if too new or already compressed
                    if file_date >= cutoff_date or file_path.suffix == ".gz":
                        continue

                    original_size = file_path.stat().st_size

                    if not dry_run:
                        # Compress the file
                        gzip_path = file_path.with_suffix(file_path.suffix + ".gz")

                        with open(file_path, "rb") as f_in:
                            with gzip.open(gzip_path, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)

                        # Remove original
                        file_path.unlink()

                        compressed_size = gzip_path.stat().st_size
                        bytes_saved += original_size - compressed_size

                        logger.info(
                            f"Compressed {file_path} "
                            f"({self._format_bytes(original_size)} -> "
                            f"{self._format_bytes(compressed_size)})"
                        )
                    else:
                        # Estimate compression ratio (typically 80%)
                        estimated_compressed = original_size * 0.2
                        bytes_saved += original_size - estimated_compressed

                    files_compressed += 1

                except OSError as e:
                    logger.warning(f"Could not compress {file_path}: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        result = CleanupResult(
            operation="compress_old_files",
            files_deleted=0,
            bytes_freed=bytes_saved,
            records_deleted=0,
            duration_seconds=duration,
            dry_run=dry_run,
            details={
                "cutoff_date": cutoff_date.isoformat(),
                "compress_days": self.compress_days,
                "files_compressed": files_compressed,
                "bytes_saved_formatted": self._format_bytes(bytes_saved),
            },
        )

        logger.info(
            f"File compression complete: {files_compressed} files, "
            f"{self._format_bytes(bytes_saved)} saved, {duration:.2f}s"
        )

        return result

    async def run_full_cleanup(
        self,
        dry_run: bool = False,
    ) -> Dict[str, CleanupResult]:
        """
        Run all cleanup operations in sequence.

        Args:
            dry_run: If True, only report what would be cleaned

        Returns:
            Dictionary with results from each operation
        """
        logger.info(f"Starting full cleanup (dry_run={dry_run})")

        results = {}

        # Cleanup old market data
        try:
            results["market_data"] = await self.cleanup_old_market_data(dry_run=dry_run)
        except Exception as e:
            logger.error(f"Error in market data cleanup: {e}")
            results["market_data"] = CleanupResult(
                operation="cleanup_old_market_data",
                files_deleted=0,
                bytes_freed=0,
                records_deleted=0,
                duration_seconds=0,
                dry_run=dry_run,
                details={"error": str(e)},
            )

        # Cleanup old logs
        try:
            results["logs"] = await self.cleanup_old_logs(dry_run=dry_run)
        except Exception as e:
            logger.error(f"Error in log cleanup: {e}")
            results["logs"] = CleanupResult(
                operation="cleanup_old_logs",
                files_deleted=0,
                bytes_freed=0,
                records_deleted=0,
                duration_seconds=0,
                dry_run=dry_run,
                details={"error": str(e)},
            )

        # Compress old files
        try:
            results["compression"] = await self.compress_old_files(dry_run=dry_run)
        except Exception as e:
            logger.error(f"Error in file compression: {e}")
            results["compression"] = CleanupResult(
                operation="compress_old_files",
                files_deleted=0,
                bytes_freed=0,
                records_deleted=0,
                duration_seconds=0,
                dry_run=dry_run,
                details={"error": str(e)},
            )

        # Summary
        total_files = results["market_data"].files_deleted
        total_bytes = results["market_data"].bytes_freed + results["compression"].bytes_freed
        total_records = results["logs"].records_deleted

        logger.info(
            f"Full cleanup complete: {total_files} files, {total_records} records, "
            f"{self._format_bytes(total_bytes)} freed/recovered"
        )

        return results

    def _update_metadata_after_cleanup(self, symbol: str, cutoff_date: date) -> None:
        """
        Update metadata after cleanup to remove deleted file entries.

        Args:
            symbol: Trading symbol
            cutoff_date: Cutoff date for cleanup
        """
        import json

        metadata_file = self.time_series_storage.metadata_path / f"{symbol}.json"

        if not metadata_file.exists():
            return

        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            # Remove entries for deleted files
            updated_metadata = {}
            for rel_path, file_info in metadata.items():
                try:
                    file_date = datetime.fromisoformat(file_info["start_time"]).date()

                    # Keep only files newer than cutoff
                    if file_date >= cutoff_date:
                        updated_metadata[rel_path] = file_info

                except (ValueError, KeyError):
                    # Keep entries with unparseable dates
                    updated_metadata[rel_path] = file_info

            # Save updated metadata
            with open(metadata_file, "w") as f:
                json.dump(updated_metadata, f, indent=2)

            logger.debug(f"Updated metadata for {symbol}: removed {len(metadata) - len(updated_metadata)} entries")

        except Exception as e:
            logger.warning(f"Could not update metadata for {symbol}: {e}")

    def get_retention_config(self) -> Dict[str, Any]:
        """
        Get current retention configuration.

        Returns:
            Dictionary with retention settings
        """
        return {
            "market_data_retention_days": self.market_retention_days,
            "log_retention_days": self.log_retention_days,
            "compress_after_days": self.compress_days,
            "market_data_path": str(self.market_data_path),
            "cutoff_dates": {
                "market_data": self._get_cutoff_date(self.market_retention_days).isoformat(),
                "logs": self._get_cutoff_date(self.log_retention_days).isoformat(),
                "compression": self._get_cutoff_date(self.compress_days).isoformat(),
            },
        }

    async def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current storage and potential cleanup.

        Returns:
            Dictionary with cleanup statistics
        """
        market_cutoff = self._get_cutoff_date(self.market_retention_days)
        log_cutoff = self._get_cutoff_date(self.log_retention_days)

        # Count old market data files
        old_market_files = 0
        old_market_size = 0

        for symbol in self.time_series_storage.get_available_symbols():
            symbol_dir = self.market_data_path / symbol

            if symbol_dir.exists():
                for file_path in symbol_dir.glob("*.parquet"):
                    try:
                        file_date = datetime.strptime(file_path.stem, "%Y-%m-%d").date()

                        if file_date < market_cutoff:
                            old_market_files += 1
                            old_market_size += file_path.stat().st_size

                    except ValueError:
                        pass

        # Count old log records
        old_log_count = 0
        if self.session:
            try:
                query = select(SystemLog).where(SystemLog.timestamp < log_cutoff)
                result = await self.session.execute(query)
                old_log_count = len(result.scalars().all())
            except Exception:
                pass

        # Current disk usage
        current_market_size = self._get_directory_size(self.market_data_path)

        return {
            "market_data": {
                "current_size_bytes": current_market_size,
                "current_size_formatted": self._format_bytes(current_market_size),
                "old_files_count": old_market_files,
                "old_files_size_bytes": old_market_size,
                "old_files_size_formatted": self._format_bytes(old_market_size),
                "cutoff_date": market_cutoff.isoformat(),
            },
            "logs": {
                "old_records_count": old_log_count,
                "cutoff_date": log_cutoff.isoformat(),
            },
            "potential_cleanup": {
                "files_deletable": old_market_files,
                "bytes_recoverable": old_market_size,
                "bytes_recoverable_formatted": self._format_bytes(old_market_size),
                "records_deletable": old_log_count,
            },
        }
