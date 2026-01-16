"""
Test database operations for EURABAY Living System.
Tests all models, CRUD operations, and database initialization.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.models.database import AsyncSessionLocal, init_db, drop_all_tables
from app.models import (
    Trade,
    PerformanceMetrics,
    ModelMetadata,
    Configuration,
    MarketData,
    Signal,
)
from app.services.database_service import DatabaseService


# Remove default handler and add custom one
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)


async def test_database_connection():
    """Test basic database connection."""
    logger.info("Testing database connection...")

    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1, "Database query failed"

        logger.success("Database connection test PASSED")
        return True
    except Exception as e:
        logger.error(f"Database connection test FAILED: {e}")
        return False


async def test_trade_crud():
    """Test Trade CRUD operations."""
    logger.info("Testing Trade CRUD operations...")

    try:
        async with AsyncSessionLocal() as session:
            db = DatabaseService(session)

            # Create
            trade = await db.create_trade(
                symbol="V10",
                direction="BUY",
                entry_price=10000.0,
                lot_size=0.01,
                confidence=0.75,
                strategy_used="test_strategy",
                stop_loss=9900.0,
                take_profit=10200.0,
            )
            assert trade.id is not None, "Trade creation failed"
            logger.info(f"Created trade with ID: {trade.id}")

            # Read
            retrieved = await db.get_by_id(Trade, trade.id)
            assert retrieved is not None, "Trade retrieval failed"
            assert retrieved.symbol == "V10", "Trade data mismatch"
            logger.info(f"Retrieved trade: {retrieved.symbol} {retrieved.direction}")

            # Update
            updated = await db.update_trade_status(
                trade.id,
                status="CLOSED",
                exit_price=10100.0,
                profit_loss=10.0,
            )
            assert updated.status == "CLOSED", "Trade update failed"
            logger.info(f"Updated trade status: {updated.status}")

            # Query open trades
            open_trades = await db.get_open_trades()
            logger.info(f"Open trades count: {len(open_trades)}")

            # Count
            count = await db.count(Trade)
            logger.info(f"Total trades: {count}")

        logger.success("Trade CRUD test PASSED")
        return True
    except Exception as e:
        logger.error(f"Trade CRUD test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_metrics():
    """Test Performance Metrics CRUD operations."""
    logger.info("Testing Performance Metrics CRUD...")

    try:
        async with AsyncSessionLocal() as session:
            db = DatabaseService(session)

            # Create
            now = datetime.utcnow()
            metrics = await db.create_performance_metrics(
                period="daily",
                period_start=now - timedelta(days=1),
                period_end=now,
                total_trades=10,
                winning_trades=7,
                losing_trades=3,
                win_rate=70.0,
                total_profit=100.0,
                total_loss=50.0,
                profit_factor=2.0,
                average_win=14.29,
                average_loss=16.67,
                max_drawdown=-20.0,
                max_drawdown_pct=2.0,
            )
            assert metrics.id is not None, "Metrics creation failed"
            logger.info(f"Created metrics with ID: {metrics.id}")

            # Read
            retrieved = await db.get_latest_metrics("daily")
            assert retrieved is not None, "Metrics retrieval failed"
            logger.info(f"Retrieved daily metrics: win_rate={retrieved.win_rate}%")

        logger.success("Performance Metrics test PASSED")
        return True
    except Exception as e:
        logger.error(f"Performance Metrics test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_configuration():
    """Test Configuration CRUD operations."""
    logger.info("Testing Configuration CRUD...")

    try:
        async with AsyncSessionLocal() as session:
            db = DatabaseService(session)

            # Create
            config = await db.set_configuration(
                config_key="test.config",
                config_value="100",
                description="Test configuration value",
                category="test",
            )
            assert config.id is not None, "Configuration creation failed"
            logger.info(f"Created configuration: {config.config_key}")

            # Read
            retrieved = await db.get_configuration("test.config")
            assert retrieved is not None, "Configuration retrieval failed"
            assert retrieved.config_value == "100", "Configuration value mismatch"
            logger.info(f"Retrieved configuration: {retrieved.config_value}")

            # Update
            updated = await db.set_configuration(
                config_key="test.config",
                config_value="200",
                description="Updated test configuration",
                category="test",
            )
            assert updated.config_value == "200", "Configuration update failed"
            logger.info(f"Updated configuration: {updated.config_value}")

            # Get all configs
            all_configs = await db.get_all_configurations()
            logger.info(f"Total configurations: {len(all_configs)}")

        logger.success("Configuration test PASSED")
        return True
    except Exception as e:
        logger.error(f"Configuration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_market_data():
    """Test Market Data CRUD operations."""
    logger.info("Testing Market Data CRUD...")

    try:
        async with AsyncSessionLocal() as session:
            db = DatabaseService(session)

            # Create
            now = datetime.utcnow()
            data = await db.create_market_data(
                symbol="V10",
                timeframe="M1",
                timestamp=now,
                open_price=10000.0,
                high_price=10050.0,
                low_price=9950.0,
                close_price=10020.0,
                volume=100,
            )
            assert data.id is not None, "Market data creation failed"
            logger.info(f"Created market data with ID: {data.id}")

            # Query
            recent = await db.get_latest_market_data("V10", "M1", limit=10)
            logger.info(f"Recent market data points: {len(recent)}")

        logger.success("Market Data test PASSED")
        return True
    except Exception as e:
        logger.error(f"Market Data test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_signals():
    """Test Signal CRUD operations."""
    logger.info("Testing Signal CRUD...")

    try:
        async with AsyncSessionLocal() as session:
            db = DatabaseService(session)

            # Create
            signal = await db.create_signal(
                symbol="V10",
                direction="BUY",
                confidence=0.85,
                price=10000.0,
                strategy="test_strategy",
                reasons=["RSI oversold", "Price support"],
            )
            assert signal.id is not None, "Signal creation failed"
            logger.info(f"Created signal with ID: {signal.id}")

            # Query recent signals
            recent = await db.get_recent_signals(hours=24, limit=10)
            logger.info(f"Recent signals: {len(recent)}")

            # Mark as executed
            executed = await db.mark_signal_executed(signal.id, trade_id=1)
            assert executed.executed is True, "Signal execution update failed"
            logger.info(f"Marked signal as executed: {executed.executed}")

        logger.success("Signal test PASSED")
        return True
    except Exception as e:
        logger.error(f"Signal test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all database tests."""
    logger.info("=" * 60)
    logger.info("Starting Database Tests")
    logger.info("=" * 60)

    tests = [
        ("Database Connection", test_database_connection),
        ("Trade CRUD", test_trade_crud),
        ("Performance Metrics", test_performance_metrics),
        ("Configuration", test_configuration),
        ("Market Data", test_market_data),
        ("Signals", test_signals),
    ]

    results = []
    for name, test_func in tests:
        logger.info("-" * 60)
        result = await test_func()
        results.append((name, result))

    # Print summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        logger.info(f"{symbol} {name}: {status}")

    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")

    if passed == total:
        logger.success("All tests PASSED!")
        return True
    else:
        logger.error(f"{total - passed} test(s) FAILED")
        return False


if __name__ == "__main__":
    # Initialize database first
    logger.info("Initializing database...")
    asyncio.run(init_db())

    # Run tests
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
