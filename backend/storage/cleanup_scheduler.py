"""
Cleanup scheduler for automated data retention operations.

This module provides a scheduler that runs cleanup operations at scheduled times.
"""

import asyncio
from datetime import datetime, time
from typing import Optional, Callable, Awaitable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from .data_retention_service import DataRetentionService


class CleanupScheduler:
    """
    Scheduler for automated cleanup operations.

    Runs cleanup tasks at specified times (default: 2 AM daily).
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        cleanup_time: time = time(2, 0),  # 2 AM
        market_data_path: str = "backend/data/market",
        market_retention_days: int = 90,
        log_retention_days: int = 30,
        compress_days: int = 7,
    ):
        """
        Initialize cleanup scheduler.

        Args:
            session_factory: Factory function to create database sessions
            cleanup_time: Time to run cleanup (default: 2:00 AM)
            market_data_path: Path to market data storage
            market_retention_days: Days to keep market data
            log_retention_days: Days to keep logs
            compress_days: Age in days before compressing files
        """
        self.session_factory = session_factory
        self.cleanup_time = cleanup_time
        self.market_data_path = market_data_path
        self.market_retention_days = market_retention_days
        self.log_retention_days = log_retention_days
        self.compress_days = compress_days

        self._running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(
            f"CleanupScheduler initialized: cleanup_time={cleanup_time}, "
            f"market_retention={market_retention_days}d, log_retention={log_retention_days}d"
        )

    async def _run_cleanup_task(self) -> None:
        """
        Main cleanup task that runs continuously.
        Checks if it's time to run cleanup and executes if so.
        """
        logger.info("Cleanup scheduler task started")

        while self._running:
            now = datetime.now()
            scheduled_time = datetime.combine(now.date(), self.cleanup_time)

            # If scheduled time has passed today, schedule for tomorrow
            if now.time() >= self.cleanup_time:
                from datetime import timedelta
                scheduled_time = scheduled_time + timedelta(days=1)

            # Calculate seconds until next cleanup
            wait_seconds = (scheduled_time - now).total_seconds()

            logger.info(
                f"Next cleanup scheduled for {scheduled_time} "
                f"(in {wait_seconds / 3600:.1f} hours)"
            )

            # Wait until scheduled time
            try:
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                logger.info("Cleanup scheduler task cancelled")
                break

            # Run cleanup if still running
            if self._running:
                await self._execute_cleanup()

        logger.info("Cleanup scheduler task stopped")

    async def _execute_cleanup(self) -> None:
        """
        Execute the cleanup operation.
        """
        logger.info("=" * 60)
        logger.info("Starting scheduled cleanup operation")
        logger.info("=" * 60)

        try:
            # Create a new session for this cleanup
            async with self.session_factory() as session:
                # Create DataRetentionService
                retention_service = DataRetentionService(
                    session=session,
                    market_data_path=self.market_data_path,
                    market_retention_days=self.market_retention_days,
                    log_retention_days=self.log_retention_days,
                    compress_days=self.compress_days,
                )

                # Run full cleanup
                results = await retention_service.run_full_cleanup(dry_run=False)

                # Log results summary
                market_result = results.get("market_data")
                log_result = results.get("logs")
                compress_result = results.get("compression")

                logger.info("Scheduled cleanup results:")
                if market_result:
                    logger.info(
                        f"  Market data: {market_result.files_deleted} files, "
                        f"{market_result.details.get('bytes_freed_formatted', 'N/A')} freed"
                    )

                if log_result:
                    logger.info(
                        f"  Logs: {log_result.records_deleted} records deleted"
                    )

                if compress_result:
                    logger.info(
                        f"  Compression: {compress_result.details.get('files_compressed', 0)} files, "
                        f"{compress_result.details.get('bytes_saved_formatted', 'N/A')} saved"
                    )

                logger.info("=" * 60)
                logger.info("Scheduled cleanup operation completed successfully")
                logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during scheduled cleanup: {e}", exc_info=True)

    async def start(self) -> None:
        """
        Start the cleanup scheduler.

        Creates an async task that runs cleanup at scheduled times.
        """
        if self._running:
            logger.warning("Cleanup scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_cleanup_task())
        logger.info("Cleanup scheduler started")

    async def stop(self) -> None:
        """
        Stop the cleanup scheduler.

        Cancels the cleanup task and waits for it to complete.
        """
        if not self._running:
            logger.warning("Cleanup scheduler is not running")
            return

        logger.info("Stopping cleanup scheduler...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Cleanup scheduler stopped")

    def is_running(self) -> bool:
        """
        Check if the scheduler is currently running.

        Returns:
            True if scheduler is running
        """
        return self._running

    async def run_once(self) -> None:
        """
        Run cleanup once immediately, without affecting the schedule.

        Useful for manual cleanup triggers or testing.
        """
        logger.info("Running manual cleanup operation")

        async with self.session_factory() as session:
            retention_service = DataRetentionService(
                session=session,
                market_data_path=self.market_data_path,
                market_retention_days=self.market_retention_days,
                log_retention_days=self.log_retention_days,
                compress_days=self.compress_days,
            )

            await retention_service.run_full_cleanup(dry_run=False)

        logger.info("Manual cleanup operation completed")


# Singleton instance for application-wide use
_scheduler_instance: Optional[CleanupScheduler] = None


def get_scheduler(
    session_factory: Callable[[], AsyncSession],
    cleanup_time: time = time(2, 0),
    market_data_path: str = "backend/data/market",
    market_retention_days: int = 90,
    log_retention_days: int = 30,
    compress_days: int = 7,
) -> CleanupScheduler:
    """
    Get or create the singleton CleanupScheduler instance.

    Args:
        session_factory: Factory function to create database sessions
        cleanup_time: Time to run cleanup (default: 2:00 AM)
        market_data_path: Path to market data storage
        market_retention_days: Days to keep market data
        log_retention_days: Days to keep logs
        compress_days: Age in days before compressing files

    Returns:
        CleanupScheduler instance
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = CleanupScheduler(
            session_factory=session_factory,
            cleanup_time=cleanup_time,
            market_data_path=market_data_path,
            market_retention_days=market_retention_days,
            log_retention_days=log_retention_days,
            compress_days=compress_days,
        )

    return _scheduler_instance
