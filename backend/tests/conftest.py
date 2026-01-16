"""
Pytest configuration and fixtures for EURABAY backend tests.

Provides database session fixtures and test utilities.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.models import (
    Trade,
    PerformanceMetrics,
    ModelMetadata,
    Configuration,
    MarketData,
    Signal,
    SystemLog,
)
from app.services.database_service import DatabaseService


# ============================================================================
# Database Engine and Session Fixtures
# ============================================================================

@pytest.fixture
async def test_engine():
    """
    Create test database engine.

    Uses in-memory SQLite for fast test execution.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session.

    Each test gets a fresh session with rolled back transactions.
    """
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        # Rollback changes after test
        await session.rollback()


# ============================================================================
# Model Data Fixtures
# ============================================================================

@pytest.fixture
async def sample_trade(test_session: AsyncSession) -> Trade:
    """Create sample trade for testing."""
    trade = Trade(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1000,
        lot_size=0.1,
        confidence=0.85,
        strategy_used="momentum",
        status="OPEN",
    )
    test_session.add(trade)
    await test_session.flush()
    await test_session.refresh(trade)
    return trade


@pytest.fixture
async def sample_market_data(test_session: AsyncSession) -> MarketData:
    """Create sample market data for testing."""
    data = MarketData(
        symbol="EURUSD",
        timeframe="H1",
        timestamp=datetime.utcnow(),
        open_price=1.1000,
        high_price=1.1010,
        low_price=1.0990,
        close_price=1.1005,
        volume=1000,
    )
    test_session.add(data)
    await test_session.flush()
    await test_session.refresh(data)
    return data


@pytest.fixture
async def sample_signal(test_session: AsyncSession, sample_trade: Trade) -> Signal:
    """Create sample signal for testing."""
    signal = Signal(
        symbol="EURUSD",
        direction="BUY",
        confidence=0.85,
        price=1.1000,
        strategy="momentum",
        reasons=["trend_up", "volume_high"],
        timestamp=datetime.utcnow(),
        executed=True,
        trade_id=sample_trade.id,
    )
    test_session.add(signal)
    await test_session.flush()
    await test_session.refresh(signal)
    return signal
