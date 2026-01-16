"""Services module for business logic."""

from .database_service import DatabaseService, get_db_service
from .query_optimizer import (
    QueryOptimizerService,
    QueryResultCache,
    QueryAnalyzer,
    PaginationResult,
    paginate_query,
    get_query_optimizer,
    log_query_time,
)
from .read_replica_service import ReadReplicaService, get_read_replica, close_read_replica
from .data_ingestion_service import (
    DataIngestionService,
    DataQuality,
    DataQualityReport,
    IngestionStats,
)

__all__ = [
    "DatabaseService",
    "get_db_service",
    "QueryOptimizerService",
    "QueryResultCache",
    "QueryAnalyzer",
    "PaginationResult",
    "paginate_query",
    "get_query_optimizer",
    "log_query_time",
    "ReadReplicaService",
    "get_read_replica",
    "close_read_replica",
    "DataIngestionService",
    "DataQuality",
    "DataQualityReport",
    "IngestionStats",
]
