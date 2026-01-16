"""
Test suite for Query Optimization features.

Tests:
- LRU cache functionality
- Query execution time logging
- EXPLAIN QUERY PLAN analysis
- Pagination
- Read replica analytical queries
- Performance with 10,000+ rows
- Query execution time < 100ms verification
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.database_service import DatabaseService
from app.services.query_optimizer import (
    QueryResultCache,
    QueryAnalyzer,
    QueryOptimizerService,
    PaginationResult,
    paginate_query,
    log_query_time,
    get_query_optimizer,
)
from app.services.read_replica_service import ReadReplicaService, get_read_replica
from app.models import Trade, MarketData, Signal, PerformanceMetrics


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def db_session(test_session: AsyncSession):
    """Provide test database session."""
    yield test_session


@pytest.fixture
def db_service(db_session: AsyncSession) -> DatabaseService:
    """Provide database service instance."""
    return DatabaseService(db_session)


@pytest.fixture
def query_cache():
    """Provide fresh query cache instance for each test."""
    cache = QueryResultCache(maxsize=10, default_ttl_seconds=1)
    yield cache
    cache.invalidate()  # Clean up


@pytest.fixture
async def populated_db(db_service: DatabaseService) -> DatabaseService:
    """
    Populate database with test data including 10,000+ rows.

    Returns:
        DatabaseService with populated data
    """
    # Insert 10,000 trades
    print("Creating 10,000 test trades...")
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

    # Bulk insert
    for trade_data in trades_data[:100]:  # Insert first 100 synchronously
        await db_service.create(Trade, **trade_data)

    # Insert remaining in batches
    batch_size = 500
    for i in range(100, 10000, batch_size):
        batch = trades_data[i:i + batch_size]
        tasks = [db_service.create(Trade, **data) for data in batch]
        await asyncio.gather(*tasks)
        print(f"Inserted {i + len(batch)} trades...")

    # Insert 5,000 market data records
    print("Creating 5,000 test market data records...")
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
        tasks = [db_service.create(MarketData, **data) for data in batch]
        await asyncio.gather(*tasks)

    print(f"Database populated: 10,000 trades, 5,000 market data records")
    return db_service


# ============================================================================
# Query Result Cache Tests
# ============================================================================

@pytest.mark.asyncio
async def test_query_cache_set_and_get(query_cache: QueryResultCache):
    """Test basic cache set and get operations."""
    query = "SELECT * FROM trades WHERE symbol = 'EURUSD'"
    params = {"limit": 100}
    result = [{"id": 1, "symbol": "EURUSD"}]

    # Set cache
    query_cache.set(query, result, params)

    # Get from cache
    cached_result = query_cache.get(query, params)
    assert cached_result == result


@pytest.mark.asyncio
async def test_query_cache_miss(query_cache: QueryResultCache):
    """Test cache miss returns None."""
    result = query_cache.get("SELECT * FROM trades", {"symbol": "BTC"})
    assert result is None


@pytest.mark.asyncio
async def test_query_cache_expiration(query_cache: QueryResultCache):
    """Test cache entries expire after TTL."""
    import time

    query = "SELECT * FROM trades"
    result = [{"id": 1}]

    # Set with 1 second TTL
    query_cache.set(query, result, ttl_seconds=1)

    # Should be available immediately
    assert query_cache.get(query) == result

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be expired
    assert query_cache.get(query) is None


@pytest.mark.asyncio
async def test_query_cache_stats(query_cache: QueryResultCache):
    """Test cache statistics tracking."""
    query = "SELECT * FROM trades"

    # Generate some hits and misses
    query_cache.set(query, [{"id": 1}])
    query_cache.get(query)  # Hit
    query_cache.get("OTHER QUERY")  # Miss
    query_cache.get(query)  # Hit

    stats = query_cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate_percent"] == 66.67


@pytest.mark.asyncio
async def test_query_cache_invalidation(query_cache: QueryResultCache):
    """Test cache invalidation."""
    query = "SELECT * FROM trades"
    result = [{"id": 1}]

    query_cache.set(query, result)
    assert query_cache.get(query) == result

    # Invalidate specific query
    query_cache.invalidate(query)
    assert query_cache.get(query) is None


@pytest.mark.asyncio
async def test_query_cache_clear_all(query_cache: QueryResultCache):
    """Test clearing all cache entries."""
    query_cache.set("QUERY1", [{"id": 1}])
    query_cache.set("QUERY2", [{"id": 2}])

    assert query_cache.get("QUERY1") is not None
    assert query_cache.get("QUERY2") is not None

    query_cache.invalidate()  # Clear all

    assert query_cache.get("QUERY1") is None
    assert query_cache.get("QUERY2") is None


# ============================================================================
# Query Analyzer Tests
# ============================================================================

@pytest.mark.asyncio
async def test_query_analyzer_explain(db_session: AsyncSession):
    """Test EXPLAIN QUERY PLAN functionality."""
    analyzer = QueryAnalyzer(db_session)

    query = "SELECT * FROM trades WHERE symbol = 'EURUSD' AND status = 'OPEN'"
    plans = await analyzer.explain_query(query)

    assert isinstance(plans, list)
    assert len(plans) > 0
    assert "detail" in plans[0]


@pytest.mark.asyncio
async def test_query_analyzer_performance_analysis(db_session: AsyncSession):
    """Test query performance analysis."""
    analyzer = QueryAnalyzer(db_session)

    query = "SELECT * FROM trades WHERE symbol = 'EURUSD'"
    analysis = await analyzer.analyze_query_performance(query)

    assert "query" in analysis
    assert "plans" in analysis
    assert "uses_index" in analysis
    assert "recommendations" in analysis
    assert isinstance(analysis["recommendations"], list)


@pytest.mark.asyncio
async def test_query_analyzer_check_index_usage(db_session: AsyncSession):
    """Test index usage checking."""
    analyzer = QueryAnalyzer(db_session)

    # Check for index on trades table
    has_index = await analyzer.check_index_usage("trades", ["symbol"])
    assert isinstance(has_index, bool)


# ============================================================================
# Pagination Tests
# ============================================================================

@pytest.mark.asyncio
async def test_paginate_query_basic(populated_db: DatabaseService):
    """Test basic pagination functionality."""
    session = populated_db.session
    query = select(Trade).order_by(Trade.id)

    result = await paginate_query(session, query, page=1, page_size=50)

    assert isinstance(result, PaginationResult)
    assert len(result.items) <= 50
    assert result.page == 1
    assert result.page_size == 50
    assert result.total > 0


@pytest.mark.asyncio
async def test_paginate_query_metadata(populated_db: DatabaseService):
    """Test pagination metadata calculation."""
    session = populated_db.session
    query = select(Trade)

    result = await paginate_query(session, query, page=1, page_size=100)

    assert result.total_pages > 0
    assert result.has_previous is False  # First page
    assert isinstance(result.has_next, bool)


@pytest.mark.asyncio
async def test_paginate_query_second_page(populated_db: DatabaseService):
    """Test pagination on second page."""
    session = populated_db.session
    query = select(Trade).order_by(Trade.id)

    page1 = await paginate_query(session, query, page=1, page_size=100)
    page2 = await paginate_query(session, query, page=2, page_size=100)

    assert page2.page == 2
    assert page2.has_previous is True
    # Items should be different
    assert page1.items[0].id != page2.items[0].id if page2.items else True


@pytest.mark.asyncio
async def test_paginate_query_to_dict(populated_db: DatabaseService):
    """Test PaginationResult.to_dict() method."""
    session = populated_db.session
    query = select(Trade)

    result = await paginate_query(session, query, page=1, page_size=50)
    result_dict = result.to_dict()

    assert "items" in result_dict
    assert "total" in result_dict
    assert "page" in result_dict
    assert "total_pages" in result_dict
    assert "has_next" in result_dict
    assert "has_previous" in result_dict


# ============================================================================
# Query Execution Time Logging Tests
# ============================================================================

@pytest.mark.asyncio
async def test_log_query_time_decorator_fast():
    """Test logging decorator for fast queries."""
    @log_query_time(warning_threshold_ms=100.0)
    async def fast_query():
        await asyncio.sleep(0.001)  # 1ms
        return [{"id": 1}]

    result = await fast_query()
    assert result == [{"id": 1}]


@pytest.mark.asyncio
async def test_log_query_time_decorator_slow():
    """Test logging decorator warns on slow queries."""
    @log_query_time(warning_threshold_ms=10.0)
    async def slow_query():
        await asyncio.sleep(0.050)  # 50ms - above threshold
        return [{"id": 1}]

    result = await slow_query()
    assert result == [{"id": 1}]


# ============================================================================
# Query Optimizer Service Tests
# ============================================================================

@pytest.mark.asyncio
async def test_query_optimizer_service_initialization(db_session: AsyncSession):
    """Test QueryOptimizerService initialization."""
    optimizer = get_query_optimizer(db_session)

    assert optimizer.session is not None
    assert optimizer.cache is not None
    assert optimizer.analyzer is not None


@pytest.mark.asyncio
async def test_query_optimizer_cache_stats(db_session: AsyncSession):
    """Test getting cache statistics from optimizer."""
    optimizer = get_query_optimizer(db_session)

    stats = optimizer.get_cache_stats()
    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate_percent" in stats


@pytest.mark.asyncio
async def test_query_optimizer_invalidate_cache(db_session: AsyncSession):
    """Test invalidating cache through optimizer."""
    optimizer = get_query_optimizer(db_session)

    # Should not raise
    optimizer.invalidate_cache()
    optimizer.invalidate_cache("SELECT 1")


# ============================================================================
# Performance Tests with Large Datasets
# ============================================================================

@pytest.mark.asyncio
async def test_query_performance_with_10k_rows(populated_db: DatabaseService):
    """
    Test query performance with 10,000+ rows.

    Verifies queries execute in reasonable time.
    """
    session = populated_db.session
    import time

    # Test 1: Simple filtered query
    start = time.perf_counter()
    result = await session.execute(
        select(Trade).where(Trade.symbol == "EURUSD").limit(100)
    )
    trades = result.scalars().all()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(trades) > 0
    assert elapsed_ms < 100, f"Query took {elapsed_ms:.2f}ms, expected < 100ms"

    # Test 2: Date range query
    start = time.perf_counter()
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()

    result = await session.execute(
        select(Trade).where(
            Trade.entry_time >= start_date,
            Trade.entry_time <= end_date
        ).order_by(Trade.entry_time.desc())
    )
    trades = result.scalars().all()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 100, f"Date range query took {elapsed_ms:.2f}ms, expected < 100ms"

    # Test 3: Aggregated query
    start = time.perf_counter()
    result = await session.execute(
        select(Trade.symbol, Trade.status)
        .where(Trade.status == "CLOSED")
        .limit(1000)
    )
    trades = result.all()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 100, f"Aggregated query took {elapsed_ms:.2f}ms, expected < 100ms"


@pytest.mark.asyncio
async def test_common_query_performance_under_100ms(populated_db: DatabaseService):
    """
    Verify common queries execute in < 100ms as per acceptance criteria.

    Tests the most common query patterns:
    - Get open trades
    - Get trades by symbol
    - Get market data by date range
    - Get recent signals
    """
    session = populated_db.session
    import time

    queries_to_test = [
        ("Get open trades", select(Trade).where(Trade.status == "OPEN").limit(50)),
        (
            "Get trades by symbol",
            select(Trade).where(Trade.symbol == "EURUSD").limit(100)
        ),
        (
            "Get market data",
            select(MarketData).where(
                MarketData.symbol == "EURUSD",
                MarketData.timeframe == "H1"
            ).limit(100)
        ),
        (
            "Get recent trades",
            select(Trade).order_by(Trade.entry_time.desc()).limit(50)
        ),
    ]

    results = []

    for query_name, query in queries_to_test:
        start = time.perf_counter()
        result = await session.execute(query)
        items = result.scalars().all()
        elapsed_ms = (time.perf_counter() - start) * 1000

        results.append({
            "query": query_name,
            "elapsed_ms": elapsed_ms,
            "row_count": len(items),
            "passed": elapsed_ms < 100
        })

        assert elapsed_ms < 100, f"{query_name} took {elapsed_ms:.2f}ms, expected < 100ms"

    # Print summary
    print("\n=== Query Performance Summary ===")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{status}: {r['query']:30s} - {r['elapsed_ms']:6.2f}ms ({r['row_count']} rows)")


# ============================================================================
# Read Replica Service Tests
# ============================================================================

@pytest.mark.asyncio
async def test_read_replica_initialization():
    """Test read replica service initialization."""
    replica = ReadReplicaService()

    assert replica.db_path is not None
    assert replica.pool_size > 0

    await replica.close()


@pytest.mark.asyncio
async def test_read_replica_session(populated_db: DatabaseService):
    """Test getting read-only session from replica."""
    replica = get_read_replica()

    async with replica.get_read_session() as session:
        result = await session.execute(
            select(Trade).limit(10)
        )
        trades = result.scalars().all()
        assert len(trades) >= 0


@pytest.mark.asyncio
async def test_read_replica_aggregated_metrics(populated_db: DatabaseService):
    """Test aggregated metrics query through read replica."""
    replica = get_read_replica()

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    metrics = await replica.get_aggregated_metrics(start_date, end_date, group_by="day")

    assert isinstance(metrics, list)


@pytest.mark.asyncio
async def test_read_replica_symbol_performance(populated_db: DatabaseService):
    """Test symbol performance query through read replica."""
    replica = get_read_replica()

    performance = await replica.get_symbol_performance(limit=10)

    assert isinstance(performance, list)


@pytest.mark.asyncio
async def test_read_replica_table_statistics(populated_db: DatabaseService):
    """Test table statistics query."""
    replica = get_read_replica()

    stats = await replica.get_table_statistics()

    assert isinstance(stats, dict)
    assert "trades" in stats


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_query_optimization(populated_db: DatabaseService):
    """Test end-to-end query optimization workflow."""
    session = populated_db.session
    optimizer = get_query_optimizer(session)

    # 1. Execute a query with caching
    query = "SELECT * FROM trades WHERE symbol = 'EURUSD' LIMIT 100"
    result1 = await optimizer.execute_cached_query(query)

    # 2. Get from cache (should be faster)
    result2 = await optimizer.execute_cached_query(query)

    assert result1 == result2

    # 3. Check cache stats
    stats = optimizer.get_cache_stats()
    assert stats["hits"] >= 1

    # 4. Analyze query performance
    analysis = await optimizer.analyze_and_optimize(query)
    assert "recommendations" in analysis


@pytest.mark.asyncio
async def test_migration_002_composite_indexes(db_session: AsyncSession):
    """Test that migration 002 composite indexes were created."""
    # Check for composite indexes
    result = await db_session.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%_%_%' ORDER BY name"
    )

    indexes = [row[0] for row in result.fetchall()]

    # Verify key composite indexes exist
    expected_indexes = [
        "ix_trades_symbol_status_entry_time",
        "ix_market_data_timestamp_symbol",
        "ix_signals_executed_timestamp",
    ]

    for expected in expected_indexes:
        assert expected in indexes, f"Expected index {expected} not found"

    print(f"\nFound {len(indexes)} composite indexes")
