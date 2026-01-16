"""
Automated backup scheduler for EURABAY Living System.
Runs database backups on a scheduled basis (default: daily at 3 AM).
"""
import asyncio
from datetime import time
from typing import Optional
from loguru import logger

from storage.backup_service import BackupService


class BackupScheduler:
    """
    Scheduler for automated database backups.
    Runs backups at specified times (default: daily at 3 AM).
    """

    _instance: Optional["BackupScheduler"] = None

    def __init__(
        self,
        backup_service: Optional[BackupService] = None,
        backup_time: time = time(3, 0),  # 3 AM
        enabled: bool = True
    ):
        """
        Initialize backup scheduler.

        Args:
            backup_service: BackupService instance (creates new if None)
            backup_time: Time of day to run backup (default: 3:00 AM)
            enabled: Whether scheduler is enabled
        """
        if backup_service is None:
            backup_service = BackupService()

        self.backup_service = backup_service
        self.backup_time = backup_time
        self.enabled = enabled
        self._task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            f"BackupScheduler initialized: backup_time={backup_time}, "
            f"enabled={enabled}"
        )

    @classmethod
    def get_scheduler(cls) -> "BackupScheduler":
        """
        Get or create the singleton BackupScheduler instance.

        Returns:
            BackupScheduler instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """
        Start the backup scheduler.
        Creates an async task that runs until stop() is called.
        """
        if self._running:
            logger.warning("Backup scheduler is already running")
            return

        if not self.enabled:
            logger.info("Backup scheduler is disabled, not starting")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Backup scheduler started")

    async def stop(self) -> None:
        """
        Stop the backup scheduler.
        """
        if not self._running:
            logger.warning("Backup scheduler is not running")
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Backup scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """
        Main scheduler loop.
        Runs backups at the configured time each day.
        """
        from datetime import datetime, timedelta

        logger.info("Backup scheduler loop started")

        while self._running:
            try:
                now = datetime.now()

                # Calculate time until next backup
                next_backup = now.replace(
                    hour=self.backup_time.hour,
                    minute=self.backup_time.minute,
                    second=0,
                    microsecond=0
                )

                # If we've passed the backup time today, schedule for tomorrow
                if now >= next_backup:
                    next_backup += timedelta(days=1)

                wait_seconds = (next_backup - now).total_seconds()

                logger.info(
                    f"Next backup scheduled for: {next_backup.isoformat()} "
                    f"(in {wait_seconds / 3600:.1f} hours)"
                )

                # Wait until backup time or until scheduler is stopped
                try:
                    await asyncio.sleep(wait_seconds)
                except asyncio.CancelledError:
                    logger.info("Backup scheduler cancelled")
                    break

                # Run backup if still running
                if self._running:
                    await self._run_backup()

            except Exception as e:
                logger.error(f"Error in backup scheduler loop: {e}")
                # Wait 1 minute before retrying
                await asyncio.sleep(60)

        logger.info("Backup scheduler loop ended")

    async def _run_backup(self) -> None:
        """
        Execute a single backup operation.
        """
        try:
            logger.info("Running scheduled database backup")

            backup_info = self.backup_service.backup_database()

            logger.success(
                f"Scheduled backup completed: {backup_info.filename} "
                f"({backup_info.size_human})"
            )

            # Log backup statistics
            stats = self.backup_service.get_backup_statistics()
            logger.info(
                f"Backup statistics: {stats['total_backups']} backups, "
                f"total size: {stats['total_size_human']}"
            )

        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")

    async def run_once(self) -> None:
        """
        Run a backup immediately, regardless of schedule.
        """
        logger.info("Running manual backup")
        await self._run_backup()

    def is_running(self) -> bool:
        """
        Check if the scheduler is currently running.

        Returns:
            True if running, False otherwise
        """
        return self._running

    def get_next_backup_time(self) -> Optional[str]:
        """
        Get the time of the next scheduled backup.

        Returns:
            ISO format string of next backup time, or None if not running
        """
        if not self._running or not self.enabled:
            return None

        from datetime import datetime, timedelta

        now = datetime.now()
        next_backup = now.replace(
            hour=self.backup_time.hour,
            minute=self.backup_time.minute,
            second=0,
            microsecond=0
        )

        if now >= next_backup:
            next_backup += timedelta(days=1)

        return next_backup.isoformat()
