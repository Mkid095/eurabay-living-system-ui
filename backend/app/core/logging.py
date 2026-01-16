"""
Structured logging configuration using loguru.
"""

import sys
import os
from loguru import logger
from app.core.config import settings
from functools import wraps
from typing import Callable, Any


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

    # Info log file
    logger.add(
        os.path.join(settings.LOG_DIR, "info_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="00:00",  # New file at midnight
        retention="7 days",  # Compress after 7 days
        compression="gz",  # Gzip compression
        enqueue=True,  # Thread-safe logging
    )

    # Error log file
    logger.add(
        os.path.join(settings.LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="7 days",
        compression="gz",
        enqueue=True,
    )

    # Trading log file (for trading operations)
    logger.add(
        os.path.join(settings.LOG_DIR, "trading_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",
        retention="7 days",
        compression="gz",
        enqueue=True,
        filter=lambda record: "trading" in record["extra"].get("context", ""),
    )

    logger.info("Logging system initialized")


def log_function_entry_exit(func: Callable) -> Callable:
    """
    Decorator to log function entry and exit with parameters and return values.
    Logs function name, arguments, and execution time.
    """
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = f"{func.__module__}.{func.__name__}"
        logger.debug(f"Entering {func_name} with args={args}, kwargs={kwargs}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Exiting {func_name} with result={result}")
            return result
        except Exception as e:
            logger.error(f"Exception in {func_name}: {e}", exc_info=True)
            raise

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = f"{func.__module__}.{func.__name__}"
        logger.debug(f"Entering {func_name} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func_name} with result={result}")
            return result
        except Exception as e:
            logger.error(f"Exception in {func_name}: {e}", exc_info=True)
            raise

    # Return appropriate wrapper based on whether function is async
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# Export logger instance and decorator
__all__ = ["logger", "setup_logging", "log_function_entry_exit"]
