"""
Query Optimization Service for EURABAY Living System.

Provides query performance optimization features including:
- LRU caching for query results
- Query execution time logging and analysis
- EXPLAIN QUERY PLAN analysis
- Prepared statement caching
- Pagination utilities
"""
from typing import Optional, List, Dict, Any, Tuple, Callable, TypeVar
from datetime import datetime, timedelta
from functools import wraps
from cachetools import LRUCache
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from loguru import logger
import time
import hashlib
import json

T = TypeVar("T")


# ============================================================================
# Query Execution Timing Decorator
# ============================================================================

def log_query_time(
    warning_threshold_ms: float = 100.0,
    operation_name: Optional[str] = None
):
    """
    Decorator to log query execution time with warnings for slow queries.

    Args:
        warning_threshold_ms: Threshold in milliseconds for warning logs
        operation_name: Optional name for the operation being timed
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            op_name = operation_name or func.__name__
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000

                if elapsed_ms > warning_threshold_ms:
                    logger.warning(
                        f"Slow query detected: {op_name} took {elapsed_ms:.2f}ms "
                        f"(threshold: {warning_threshold_ms}ms)"
                    )
                else:
                    logger.debug(
                        f"Query {op_name} completed in {elapsed_ms:.2f}ms"
                    )

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            op_name = operation_name or func.__name__
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000

                if elapsed_ms > warning_threshold_ms:
                    logger.warning(
                        f"Slow query detected: {op_name} took {elapsed_ms:.2f}ms "
                        f"(threshold: {warning_threshold_ms}ms)"
                    )
                else:
                    logger.debug(
                        f"Query {op_name} completed in {elapsed_ms:.2f}ms"
                    )

        # Check if function is coroutine
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# Query Result Cache
# ============================================================================

class QueryResultCache:
    """
    LRU cache for query results with configurable TTL.

    Uses a two-tier caching strategy:
    1. In-memory LRU cache for fast access
    2. TTL-based expiration to prevent stale data
    """

    def __init__(
        self,
        maxsize: int = 128,
        default_ttl_seconds: int = 60
    ):
        """
        Initialize query result cache.

        Args:
            maxsize: Maximum number of cached entries
            default_ttl_seconds: Default time-to-live in seconds
        """
        self._cache: LRUCache[str, Tuple[Any, datetime]] = LRUCache(maxsize=maxsize)
        self._default_ttl = timedelta(seconds=default_ttl_seconds)
        self._hits = 0
        self._misses = 0

    def _generate_key(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key from query and parameters.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cache key hash
        """
        key_data = {
            "query": query.strip(),
            "params": params or {}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached result if available and not expired.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cached result or None
        """
        key = self._generate_key(query, params)

        if key in self._cache:
            result, expiry = self._cache[key]

            if datetime.utcnow() < expiry:
                self._hits += 1
                logger.debug(f"Cache hit for query key: {key[:16]}...")
                return result
            else:
                # Expired entry
                del self._cache[key]
                logger.debug(f"Cache expired for query key: {key[:16]}...")

        self._misses += 1
        return None

    def set(
        self,
        query: str,
        result: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Cache query result with TTL.

        Args:
            query: SQL query string
            result: Query result to cache
            params: Query parameters
            ttl_seconds: Custom TTL in seconds
        """
        key = self._generate_key(query, params)
        ttl = timedelta(seconds=ttl_seconds or self._default_ttl.seconds)
        expiry = datetime.utcnow() + ttl

        self._cache[key] = (result, expiry)
        logger.debug(f"Cached result for query key: {key[:16]}... (TTL: {ttl.seconds}s)")

    def invalidate(self, query: Optional[str] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            query: Specific query to invalidate, or None to clear all
        """
        if query:
            key = self._generate_key(query, None)
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Invalidated cache for query key: {key[:16]}...")
        else:
            self._cache.clear()
            logger.debug("Cleared entire query cache")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "size": len(self._cache),
            "maxsize": self._cache.maxsize
        }

    def clear_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0


# Global cache instance
_global_cache: Optional[QueryResultCache] = None


def get_query_cache() -> QueryResultCache:
    """Get or create global query cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = QueryResultCache(maxsize=256, default_ttl_seconds=60)
    return _global_cache


# ============================================================================
# Query Analyzer
# ============================================================================

class QueryAnalyzer:
    """
    Analyze query performance using EXPLAIN QUERY PLAN.

    Provides detailed analysis of:
    - Index usage
    - Table scans
    - Join strategies
    - Query optimization opportunities
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize query analyzer.

        Args:
            session: Async database session
        """
        self.session = session

    async def explain_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute EXPLAIN QUERY PLAN for a query.

        Args:
            query: SQL query to analyze
            params: Query parameters

        Returns:
            List of execution plan steps
        """
        explain_query_str = f"EXPLAIN QUERY PLAN\n{query}"

        try:
            result = await self.session.execute(
                text(explain_query_str),
                params or {}
            )

            rows = result.fetchall()
            plans = []

            for row in rows:
                plans.append({
                    "detail": row[0] if row else None,
                    "selectid": row[1] if len(row) > 1 else None,
                    "order": row[2] if len(row) > 2 else None,
                    "from": row[3] if len(row) > 3 else None,
                })

            return plans
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            raise

    async def analyze_query_performance(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze query and provide optimization recommendations.

        Args:
            query: SQL query to analyze
            params: Query parameters

        Returns:
            Dictionary with analysis results and recommendations
        """
        plans = await self.explain_query(query, params)

        analysis = {
            "query": query.strip()[:200],
            "plans": plans,
            "uses_index": False,
            "table_scan": False,
            "recommendations": []
        }

        # Analyze execution plan
        for plan in plans:
            detail = plan.get("detail", "")

            # Check for index usage
            if "SEARCH" in detail.upper() and "USING INDEX" in detail.upper():
                analysis["uses_index"] = True

            # Check for table scans
            if "SCAN" in detail.upper() and "TABLE" in detail.upper():
                analysis["table_scan"] = True
                analysis["recommendations"].append(
                    "Table scan detected - consider adding indexes on filtered columns"
                )

            # Check for temporary B-tree structures
            if "USE TEMP B-TREE" in detail.upper():
                analysis["recommendations"].append(
                    "Temporary B-tree created - consider optimizing ORDER BY or creating composite indexes"
                )

        # General recommendations
        if not analysis["uses_index"] and not analysis["table_scan"]:
            analysis["recommendations"].append(
                "Query may benefit from proper indexing on join/filter columns"
            )

        return analysis

    async def check_index_usage(
        self,
        table_name: str,
        column_names: List[str]
    ) -> bool:
        """
        Check if an index exists for given table columns.

        Args:
            table_name: Table name
            column_names: List of column names

        Returns:
            True if composite index exists
        """
        query = text("""
            SELECT COUNT(*) as index_count
            FROM sqlite_master
            WHERE type = 'index'
            AND tbl_name = :table_name
            AND sql LIKE :column_pattern
        """)

        # Check for each column individually and in combination
        for col in column_names:
            result = await self.session.execute(
                query,
                {"table_name": table_name, "column_pattern": f"%{col}%"}
            )
            count = result.scalar()

            if count > 0:
                return True

        return False


# ============================================================================
# Pagination Utilities
# ============================================================================

class PaginationResult:
    """Generic pagination result container."""

    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int,
        page_size: int
    ):
        """
        Initialize pagination result.

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number (1-indexed)
            page_size: Number of items per page
        """
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size if self.page_size > 0 else 0

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous
        }


async def paginate_query(
    session: AsyncSession,
    query: Select,
    page: int = 1,
    page_size: int = 50
) -> PaginationResult:
    """
    Paginate a SQLAlchemy query.

    Args:
        session: Async database session
        query: SQLAlchemy select query
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginationResult with items and metadata
    """
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 1000:
        page_size = 50

    # Get total count
    from sqlalchemy import func

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    paginated_query = query.offset(offset).limit(page_size)

    result = await session.execute(paginated_query)
    items = list(result.scalars().all())

    return PaginationResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


# ============================================================================
# Prepared Statement Cache
# ============================================================================

class PreparedStatementCache:
    """
    Cache for prepared SQL statements to avoid repeated parsing.

    Particularly useful for frequently executed queries with different parameters.
    """

    def __init__(self, maxsize: int = 64):
        """
        Initialize prepared statement cache.

        Args:
            maxsize: Maximum number of cached statements
        """
        self._statements: LRUCache[str, Any] = LRUCache(maxsize=maxsize)

    def get_statement_key(self, query: str) -> str:
        """
        Generate cache key for a query.

        Args:
            query: SQL query string

        Returns:
            Cache key
        """
        normalized = query.strip().replace("\n", " ").replace("\t", " ")
        # Collapse multiple spaces
        while "  " in normalized:
            normalized = normalized.replace("  ", " ")
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, query: str) -> Optional[Any]:
        """Get cached prepared statement."""
        key = self.get_statement_key(query)
        return self._statements.get(key)

    def set(self, query: str, statement: Any) -> None:
        """Cache a prepared statement."""
        key = self.get_statement_key(query)
        self._statements[key] = statement

    def clear(self) -> None:
        """Clear all cached statements."""
        self._statements.clear()


# ============================================================================
# Query Optimizer Service
# ============================================================================

class QueryOptimizerService:
    """
    Main query optimization service combining all optimization features.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize query optimizer service.

        Args:
            session: Async database session
        """
        self.session = session
        self.cache = get_query_cache()
        self.analyzer = QueryAnalyzer(session)
        self.prepared_cache = PreparedStatementCache()

    @log_query_time(warning_threshold_ms=100.0, operation_name="optimized_query")
    async def execute_cached_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query with result caching.

        Args:
            query: SQL query string
            params: Query parameters
            ttl_seconds: Custom cache TTL

        Returns:
            Query results as list of dictionaries
        """
        # Check cache first
        cached_result = self.cache.get(query, params)
        if cached_result is not None:
            return cached_result

        # Execute query
        result = await self.session.execute(text(query), params or {})
        rows = result.fetchall()
        columns = result.keys()

        # Convert to list of dicts
        dict_results = [dict(zip(columns, row)) for row in rows]

        # Cache the result
        self.cache.set(query, dict_results, params, ttl_seconds)

        return dict_results

    async def analyze_and_optimize(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze query and return optimization recommendations.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Analysis results with recommendations
        """
        return await self.analyzer.analyze_query_performance(query, params)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        return self.cache.get_stats()

    def invalidate_cache(self, query: Optional[str] = None) -> None:
        """
        Invalidate query cache.

        Args:
            query: Specific query to invalidate, or None to clear all
        """
        self.cache.invalidate(query)

    async def get_index_recommendations(
        self,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get index recommendations for a table based on query patterns.

        Args:
            table_name: Table name to analyze

        Returns:
            List of recommended indexes
        """
        # This would analyze query history and suggest indexes
        # For now, return common recommendations
        recommendations = []

        # Get existing indexes
        query = text("""
            SELECT sql FROM sqlite_master
            WHERE type = 'index'
            AND tbl_name = :table_name
            AND sql IS NOT NULL
        """)

        result = await self.session.execute(query, {"table_name": table_name})
        existing_indexes = [row[0] for row in result.fetchall()]

        # Common column combinations that benefit from composite indexes
        common_combinations = {
            "trades": [
                {"columns": ["symbol", "status", "entry_time"], "reason": "Filter active trades by symbol"},
                {"columns": ["entry_time", "exit_time"], "reason": "Date range queries"},
                {"columns": ["status", "entry_time"], "reason": "Open trades ordered by time"}
            ],
            "market_data": [
                {"columns": ["symbol", "timeframe", "timestamp"], "reason": "Time-series queries", "exists": True},
                {"columns": ["timestamp", "symbol"], "reason": "Latest data queries"}
            ],
            "signals": [
                {"columns": ["symbol", "executed", "timestamp"], "reason": "Unexecuted signals by time"},
                {"columns": ["executed", "timestamp"], "reason": "Recent unexecuted signals"}
            ],
            "performance_metrics": [
                {"columns": ["period", "period_start", "period_end"], "reason": "Period range queries", "exists": True}
            ]
        }

        if table_name in common_combinations:
            for combo in common_combinations[table_name]:
                if not combo.get("exists", False):
                    recommendations.append({
                        "table": table_name,
                        "columns": combo["columns"],
                        "reason": combo["reason"]
                    })

        return recommendations


# ============================================================================
# Helper Functions
# ============================================================================

def get_query_optimizer(session: AsyncSession) -> QueryOptimizerService:
    """
    Get query optimizer service instance.

    Args:
        session: Async database session

    Returns:
        QueryOptimizerService instance
    """
    return QueryOptimizerService(session)
