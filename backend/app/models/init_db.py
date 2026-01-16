"""
Database initialization script for EURABAY Living System.
Creates all tables and seeds initial configuration data.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

from .database import init_db, engine, AsyncSessionLocal
from .models import Configuration, ModelMetadata, PerformanceMetrics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


# Default configuration values
DEFAULT_CONFIGURATIONS = [
    {
        "config_key": "risk.max_position_risk_pct",
        "config_value": "2.0",
        "description": "Maximum risk per trade as percentage of account balance",
        "category": "risk"
    },
    {
        "config_key": "risk.max_daily_loss_pct",
        "config_value": "5.0",
        "description": "Maximum daily loss as percentage of account balance",
        "category": "risk"
    },
    {
        "config_key": "risk.max_concurrent_positions",
        "config_value": "3",
        "description": "Maximum number of concurrent open positions",
        "category": "risk"
    },
    {
        "config_key": "risk.default_risk_reward_ratio",
        "config_value": "1.5",
        "description": "Default risk-reward ratio for trades",
        "category": "risk"
    },
    {
        "config_key": "risk.atr_multiplier",
        "config_value": "1.5",
        "description": "ATR multiplier for stop loss calculation",
        "category": "risk"
    },
    {
        "config_key": "trading.symbols",
        "config_value": json.dumps(["V10", "V25", "V50", "V75", "V100"]),
        "description": "List of trading symbols",
        "category": "trading"
    },
    {
        "config_key": "trading.min_signal_confidence",
        "config_value": "0.6",
        "description": "Minimum confidence threshold for executing signals",
        "category": "trading"
    },
    {
        "config_key": "trading.signal_cooldown_seconds",
        "config_value": "60",
        "description": "Cooldown period between signals for same symbol (seconds)",
        "category": "trading"
    },
    {
        "config_key": "trading.max_trade_duration_minutes",
        "config_value": "240",
        "description": "Maximum duration for a trade before forced exit (minutes)",
        "category": "trading"
    },
    {
        "config_key": "system.paper_trading_mode",
        "config_value": "true",
        "description": "Enable paper trading mode (no real trades)",
        "category": "system"
    },
    {
        "config_key": "system.loop_interval_seconds",
        "config_value": "1",
        "description": "Trading loop execution interval (seconds)",
        "category": "system"
    },
    {
        "config_key": "system.enable_continuous_learning",
        "config_value": "false",
        "description": "Enable automatic model retraining",
        "category": "system"
    },
    {
        "config_key": "system.retraining_interval_hours",
        "config_value": "168",
        "description": "Interval for model retraining (hours, default 1 week)",
        "category": "system"
    },
    {
        "config_key": "logging.log_level",
        "config_value": "INFO",
        "description": "Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        "category": "system"
    },
    {
        "config_key": "logging.log_retention_days",
        "config_value": "90",
        "description": "Number of days to retain log files",
        "category": "system"
    },
]


async def seed_configurations(session: AsyncSession):
    """
    Seed default configurations into the database.

    Args:
        session: Async database session
    """
    logger.info("Seeding default configurations...")

    for config_data in DEFAULT_CONFIGURATIONS:
        # Check if configuration already exists
        result = await session.execute(
            select(Configuration).where(
                Configuration.config_key == config_data["config_key"]
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            config = Configuration(**config_data)
            session.add(config)
            logger.info(f"Added configuration: {config_data['config_key']}")
        else:
            logger.debug(f"Configuration already exists: {config_data['config_key']}")

    await session.commit()
    logger.info("Configurations seeded successfully")


async def seed_initial_performance_metrics(session: AsyncSession):
    """
    Create initial performance metrics record.

    Args:
        session: Async database session
    """
    logger.info("Creating initial performance metrics...")

    # Check if metrics already exist
    result = await session.execute(
        select(PerformanceMetrics).where(
            PerformanceMetrics.period == "all_time"
        )
    )
    existing = result.scalar_one_or_none()

    if not existing:
        now = datetime.utcnow()
        metrics = PerformanceMetrics(
            period="all_time",
            period_start=now,
            period_end=now,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit=0.0,
            total_loss=0.0,
            profit_factor=0.0,
            average_win=0.0,
            average_loss=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
        )
        session.add(metrics)
        await session.commit()
        logger.info("Initial performance metrics created")
    else:
        logger.debug("Performance metrics already exist")


async def initialize_database():
    """
    Initialize database with tables and seed data.
    """
    logger.info("Initializing EURABAY Living System database...")

    try:
        # Create all tables
        await init_db()
        logger.info("Database tables created successfully")

        # Seed initial data
        async with AsyncSessionLocal() as session:
            await seed_configurations(session)
            await seed_initial_performance_metrics(session)

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def reset_database():
    """
    Reset database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST!")

    from .database import drop_all_tables

    try:
        # Drop all tables
        await drop_all_tables()
        logger.info("All tables dropped")

        # Reinitialize
        await initialize_database()
        logger.info("Database reset completed")

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


async def verify_database():
    """
    Verify database integrity by checking table counts.

    Returns:
        dict: Verification results
    """
    logger.info("Verifying database...")

    results = {}

    try:
        async with AsyncSessionLocal() as session:
            # Check configurations
            result = await session.execute(select(Configuration))
            configs = result.scalars().all()
            results["configurations"] = len(configs)
            logger.info(f"Configurations: {len(configs)}")

            # Check performance metrics
            result = await session.execute(select(PerformanceMetrics))
            metrics = result.scalars().all()
            results["performance_metrics"] = len(metrics)
            logger.info(f"Performance metrics: {len(metrics)}")

            # Check models
            result = await session.execute(select(ModelMetadata))
            models = result.scalars().all()
            results["models"] = len(models)
            logger.info(f"Models: {len(models)}")

        logger.info("Database verification completed")
        return results

    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise


def main():
    """
    Main entry point for database initialization.
    """
    import sys

    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "init":
            asyncio.run(initialize_database())
        elif command == "reset":
            confirm = input("Are you sure you want to reset the database? (yes/no): ")
            if confirm.lower() == "yes":
                asyncio.run(reset_database())
            else:
                logger.info("Reset cancelled")
        elif command == "verify":
            results = asyncio.run(verify_database())
            print("\nDatabase Verification Results:")
            for key, value in results.items():
                print(f"  {key}: {value}")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: init, reset, verify")
    else:
        print("Usage: python init_db.py [init|reset|verify]")
        print("  init   - Initialize database with tables and seed data")
        print("  reset  - Reset database (WARNING: deletes all data)")
        print("  verify - Verify database integrity")


if __name__ == "__main__":
    main()
