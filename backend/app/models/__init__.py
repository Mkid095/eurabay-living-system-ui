"""
Models module for database and Pydantic models.
Exports all SQLAlchemy models and schemas for easy importing.
"""

# Import all SQLAlchemy models
from .models import (
    Trade,
    PerformanceMetrics,
    ModelMetadata,
    Configuration,
    MarketData,
    Signal,
)

# Import database configuration
from .database import (
    Base,
    engine,
    AsyncSessionLocal,
    get_db,
    init_db,
    drop_all_tables,
    close_db,
)

# Import Pydantic schemas (renamed to avoid conflicts with SQLAlchemy models)
from .schemas import (
    TradeBase,
    TradeCreate,
    TradeUpdate,
    TradeSchema,
    PerformanceMetricsBase,
    PerformanceMetricsCreate,
    PerformanceMetricsSchema,
    ModelMetadataBase,
    ModelMetadataCreate,
    ModelMetadataSchema,
    ConfigurationBase,
    ConfigurationCreate,
    ConfigurationSchema,
    MarketDataBase,
    MarketDataCreate,
    MarketDataSchema,
    SignalBase,
    SignalCreate,
    SignalSchema,
    HealthResponse,
    AccountInfoResponse,
    ErrorResponse,
)

__all__ = [
    # SQLAlchemy Models
    "Trade",
    "PerformanceMetrics",
    "ModelMetadata",
    "Configuration",
    "MarketData",
    "Signal",
    # Database
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "drop_all_tables",
    "close_db",
    # Pydantic Schemas (with Schema suffix to avoid conflicts)
    "TradeBase",
    "TradeCreate",
    "TradeUpdate",
    "TradeSchema",
    "PerformanceMetricsBase",
    "PerformanceMetricsCreate",
    "PerformanceMetricsSchema",
    "ModelMetadataBase",
    "ModelMetadataCreate",
    "ModelMetadataSchema",
    "ConfigurationBase",
    "ConfigurationCreate",
    "ConfigurationSchema",
    "MarketDataBase",
    "MarketDataCreate",
    "MarketDataSchema",
    "SignalBase",
    "SignalCreate",
    "SignalSchema",
    "HealthResponse",
    "AccountInfoResponse",
    "ErrorResponse",
]
