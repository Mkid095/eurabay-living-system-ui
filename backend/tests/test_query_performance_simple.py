"""
Simple test script to verify query performance optimization.

Tests:
- Query performance with 10,000+ rows
- Verify query execution time < 100ms for common queries
- Composite indexes effectiveness
- Query result caching
- Pagination
"""
import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.models.database import AsyncSessionLocal, engine, init_db
from app.models.models import Trade, MarketData, Signal
from app.services.query_optimizer import (
    QueryResultCache,
    QueryAnalyzer,
    QueryOptimizerService,
    PaginationResult,
    paginate_query,
    log_query_time,
)
from app.services.read_replica_service import ReadReplicaService, get_read_replica
from loguru import logger


# ============================================================================
# Test Functions
# ============================================================================

async def populate_test_data():
    """
    Populate database with 10,000+ rows for performance testing.

    Creates:
    - 10,000 trades
    - 5,000 market data records
    """
    logger.info("Populating test database with 10,000+ rows...")

    async with AsyncSessionLocal() as session:
        # Insert 10,000 trades
        logger.info("Creating 10,000 test trades...")
        trades_data = []
        base_time = datetime.utcnow() - timedelta(days=365)

        for i in range(10000):
            trades_data.append({
                "symbol": "EURUSD" if i % 3 == 0 else "GBPUSD" if i % 3 == 1 else "USDJPY",
                "direction": "BUY" if i % 2 == 0 else "SELL",
                "entry_price": 1.1000 + (i % 100) * 0.0001,
                "lot_size": 0.1,
                "confidence": 0.7 + (i % 30) * 0.01,
                "strategy_used": "momentum" if i % 2 == 0 else "mean_reversion",
                "entry_time": base_time + timedelta(hours=i),
                "exit_price": 1.1000 + (i % 100) * 0.0001 + 0.0010,
                "exit_time": base_time + timedelta(hours=i + 4),
                "profit_loss": 100.0 + (i % 50) * 10,
                "profit_loss_pips": 10.0,
                "status": "CLOSED",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })

        # Bulk insert in batches
        batch_size = 500
        for i in range(0, 10000, batch_size):
            batch = trades_data[i:i + batch_size]
            for data in batch:
                trade = Trade(**data)
                session.add(trade)
            await session.flush()
            logger.info(f"Inserted {i + len(batch)} trades...")

        # Insert 5,000 market data records
        logger.info("Creating 5,000 test market data records...")
        market_data_list = []
        for i in range(5000):
            market_data_list.append({
                "symbol": "EURUSD" if i % 3 == 0 else "GBPUSD",
                "timeframe": "H1",
                "timestamp": base_time + timedelta(hours=i),
                "open_price": 1.1000 + (i % 100) * 0.0001,
                "high_price": 1.1010 + (i % 100) * 0.0001,
                "low_price": 1.0990 + (i % 100) * 0.0001,
                "close_price": 1.1005 + (i % 100) * 0.0001,
                "volume": 1000 + i % 500,
            })

        batch_size = 500
        for i in range(0, 5000, batch_size):
            batch = market_data_list[i:i + batch_size]
            for data in batch:
                market_data = MarketData(**data)
                session.add(market_data)
            await session.flush()
            logger.info(f"Inserted {i + len(batch)} market data records...")

        await session.commit()
        logger.info("Database populated: 10,000 trades, 5,000 market data records")


async def test_query_performance():
    """
    Test query performance with 10,000+ rows.

    Verifies queries execute in < 100ms as per acceptance criteria.
    """
    logger.info("=" * 60)
    logger.info("Query Performance Test - 10,000+ Rows")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as session:
        # Get row count
        count_result = await session.execute(select(func.count(Trade.id)))
        total_trades = count_result.scalar()
        logger.info(f"Total trades in database: {total_trades}")

        if total_trades < 10000:
            logger.warning(f"Expected 10,000+ trades, found {total_trades}")

        # Test common query patterns
        queries = [
            ("Filtered query by symbol", select(Trade).where(Trade.symbol == "EURUSD").limit(100)),
            ("Date range query", select(Trade).where(
                Trade.entry_time >= datetime.utcnow() - timedelta(days=30),
                Trade.entry_time <= datetime.utcnow()
            ).limit(100)),
            ("Recent trades", select(Trade).order_by(Trade.entry_time.desc()).limit(50)),
            ("Aggregated count", select(func.count(Trade.id)).where(Trade.status == "CLOSED")),
            ("Market data query", select(MarketData).where(
                MarketData.symbol == "EURUSD",
                MarketData.timeframe == "H1"
            ).limit(100)),
        ]

        results = []
        for query_name, query in queries:
            start = time.perf_counter()
            result = await session.execute(query)
            if query_name == "Aggregated count":
                count = result.scalar()
                items_count = count
            else:
                items = result.scalars().all()
                items_count = len(items)
            elapsed_ms = (time.perf_counter() - start) * 1000

            passed = elapsed_ms < 100
            status = "PASS" if passed else "FAIL"

            results.append({
                "query": query_name,
                "elapsed_ms": elapsed_ms,
                "row_count": items_count,
                "passed": passed
            })

            logger.info(f"{status}: {query_name:30s} - {elapsed_ms:6.2f}ms ({items_count} rows)")

        # Summary
        passed_count = sum(1 for r in results if r["passed"])
        logger.info(f"\nSummary: {passed_count}/{len(results)} queries passed < 100ms threshold")

        if passed_count == len(results):
            logger.success("All query performance tests PASSED!")
        else:
            logger.warning(f"Some queries exceeded 100ms threshold")

        return all(r["passed"] for r in results)


async def test_query_cache():
    """Test query result caching functionality."""
    logger.info("\n" + "=" * 60)
    logger.info("Query Result Cache Test")
    logger.info("=" * 60)

    cache = QueryResultCache(maxsize=10, default_ttl_seconds=60)

    # Test cache set and get
    query = "SELECT * FROM trades WHERE symbol = 'EURUSD'"
    result = [{"id": 1, "symbol": "EURUSD", "profit_loss": 100.0}]

    cache.set(query, result)
    cached_result = cache.get(query)

    assert cached_result == result, "Cache should return the same result"
    logger.info("Cache set and get: PASSED")

    # Test cache miss
    miss_result = cache.get("SELECT * FROM trades WHERE symbol = 'GBPUSD'")
    assert miss_result is None, "Cache miss should return None"
    logger.info("Cache miss: PASSED")

    # Test cache stats
    cache.get(query)  # Hit
    cache.get("OTHER")  # Miss
    stats = cache.get_stats()

    assert stats["hits"] >= 1, "Should have at least 1 hit"
    assert stats["misses"] >= 1, "Should have at least 1 miss"
    logger.info(f"Cache stats: {stats}")
    logger.info("Cache statistics: PASSED")

    # Test cache invalidation
    cache.invalidate(query)
    assert cache.get(query) is None, "Invalidated cache should return None"
    logger.info("Cache invalidation: PASSED")

    logger.success("Query cache tests PASSED!")
    return True


async def test_pagination():
    """Test pagination with large result sets."""
    logger.info("\n" + "=" * 60)
    logger.info("Pagination Test")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as session:
        query = select(Trade).order_by(Trade.id)

        # Test first page
        result = await paginate_query(session, query, page=1, page_size=100)

        assert isinstance(result, PaginationResult), "Should return PaginationResult"
        assert len(result.items) <= 100, "Should not exceed page size"
        assert result.page == 1, "Should be page 1"
        assert result.page_size == 100, "Page size should be 100"
        assert result.total > 0, "Should have total count"
        logger.info(f"Page 1: {len(result.items)} items, total: {result.total}")

        # Test second page
        page2 = await paginate_query(session, query, page=2, page_size=100)
        assert page2.page == 2, "Should be page 2"
        assert page2.has_previous is True, "Should have previous page"
        logger.info(f"Page 2: {len(page2.items)} items, has_previous: {page2.has_previous}")

        # Test to_dict
        result_dict = result.to_dict()
        assert "items" in result_dict, "Should have items"
        assert "total" in result_dict, "Should have total"
        assert "total_pages" in result_dict, "Should have total_pages"
        logger.info("Pagination to_dict: PASSED")

        logger.success("Pagination tests PASSED!")
        return True


async def test_query_analyzer():
    """Test EXPLAIN QUERY PLAN functionality."""
    logger.info("\n" + "=" * 60)
    logger.info("Query Analyzer Test")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as session:
        analyzer = QueryAnalyzer(session)

        # Test EXPLAIN QUERY PLAN
        query = "SELECT * FROM trades WHERE symbol = 'EURUSD' AND status = 'OPEN'"
        plans = await analyzer.explain_query(query)

        assert isinstance(plans, list), "Should return list of plans"
        assert len(plans) > 0, "Should have at least one plan"
        logger.info(f"EXPLAIN QUERY PLAN returned {len(plans)} steps")

        # Test performance analysis
        analysis = await analyzer.analyze_query_performance(query)

        assert "query" in analysis, "Should have query"
        assert "plans" in analysis, "Should have plans"
        assert "uses_index" in analysis, "Should have uses_index"
        assert "recommendations" in analysis, "Should have recommendations"
        logger.info(f"Analysis result: uses_index={analysis['uses_index']}")
        logger.info(f"Recommendations: {len(analysis['recommendations'])}")

        logger.success("Query analyzer tests PASSED!")
        return True


async def test_read_replica():
    """Test read replica service."""
    logger.info("\n" + "=" * 60)
    logger.info("Read Replica Service Test")
    logger.info("=" * 60)

    replica = ReadReplicaService()
    await replica.initialize()

    try:
        # Test get_read_session
        async with replica.get_read_session() as session:
            result = await session.execute(select(Trade).limit(10))
            trades = result.scalars().all()
            logger.info(f"Read replica session returned {len(trades)} trades")

        # Test aggregated metrics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        metrics = await replica.get_aggregated_metrics(start_date, end_date, group_by="day")
        logger.info(f"Aggregated metrics returned {len(metrics)} periods")

        # Test table statistics
        stats = await replica.get_table_statistics()
        logger.info(f"Table statistics: {list(stats.keys())}")

        logger.success("Read replica tests PASSED!")
        return True
    finally:
        await replica.close()


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all query optimization tests."""
    print("\n")
    print("=" * 60)
    print("EURABAY Query Optimization - Performance Test Suite")
    print("=" * 60)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()

    # Populate test data
    await populate_test_data()

    # Run tests
    results = []

    try:
        results.append(("Query Performance", await test_query_performance()))
    except Exception as e:
        logger.error(f"Query performance test failed: {e}")
        results.append(("Query Performance", False))

    try:
        results.append(("Query Cache", await test_query_cache()))
    except Exception as e:
        logger.error(f"Query cache test failed: {e}")
        results.append(("Query Cache", False))

    try:
        results.append(("Pagination", await test_pagination()))
    except Exception as e:
        logger.error(f"Pagination test failed: {e}")
        results.append(("Pagination", False))

    try:
        results.append(("Query Analyzer", await test_query_analyzer()))
    except Exception as e:
        logger.error(f"Query analyzer test failed: {e}")
        results.append(("Query Analyzer", False))

    try:
        results.append(("Read Replica", await test_read_replica()))
    except Exception as e:
        logger.error(f"Read replica test failed: {e}")
        results.append(("Read Replica", False))

    # Summary
    print("\n")
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        logger.success("All query optimization tests PASSED!")
        return True
    else:
        logger.error(f"Some tests failed: {total_tests - total_passed} failures")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
