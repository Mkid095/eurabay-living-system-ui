"""
Structured logging configuration using loguru.
"""

import sys
import os
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging with loguru.
    Removes default handler and adds custom handlers.
    """
    # Remove default handler
    logger.remove()

    # Ensure log directory exists
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    # Console handler with formatting
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
    )

    # File handler for all logs
    logger.add(
        os.path.join(settings.LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # New file at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip",
        enqueue=True,  # Thread-safe logging
    )

    # Error log file
    logger.add(
        os.path.join(settings.LOG_DIR, "errors_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="90 days",
        compression="zip",
        enqueue=True,
    )

    logger.info("Logging system initialized")


# Export logger instance
__all__ = ["logger", "setup_logging"]
