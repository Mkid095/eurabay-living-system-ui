"""
Simple test script to verify SQLAlchemy async models work.
This script runs each test in sequence to avoid database locking issues.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.database import AsyncSessionLocal, init_db
from app.models.models import (
    Trade,
    PerformanceMetrics,
    ModelMetadata,
    Configuration,
    MarketData,
    Signal,
    SystemLog,
)


async def test_all_models():
    """Test all models sequentially."""
    print("=" * 60)
    print("SQLAlchemy Async Models Test - Sequential Run")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database...")
    await init_db()
    print("   Database initialized")

    async with AsyncSessionLocal() as session:
        # Test 1: Create a Trade
        print("\n2. Testing Trade model...")
        trade = Trade(
            symbol="V100",
            direction="BUY",
            entry_price=1.0900,
            lot_size=0.01,
            confidence=0.85,
            strategy_used="TestStrategy",
            status="OPEN",
        )
        session.add(trade)
        await session.flush()
        await session.refresh(trade)
        print(f"   Created trade: {trade}")
        print(f"   __repr__: {repr(trade)}")
        trade_dict = trade.to_dict()
        print(f"   to_dict() keys: {list(trade_dict.keys())}")
        assert trade.symbol == "V100"
        assert trade.direction == "BUY"
        print("   Trade model PASSED")

        # Test 2: Create PerformanceMetrics
        print("\n3. Testing PerformanceMetrics model...")
        metrics = PerformanceMetrics(
            period="daily",
            period_start=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow(),
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            profit_factor=2.5,
        )
        session.add(metrics)
        await session.flush()
        await session.refresh(metrics)
        print(f"   Created metrics: {metrics}")
        print(f"   __repr__: {repr(metrics)}")
        metrics_dict = metrics.to_dict()
        print(f"   to_dict() keys: {list(metrics_dict.keys())}")
        assert metrics.period == "daily"
        assert metrics.win_rate == 60.0
        print("   PerformanceMetrics model PASSED")

        # Test 3: Create ModelMetadata
        print("\n4. Testing ModelMetadata model...")
        model = ModelMetadata(
            model_name="XGBoostTest",
            model_type="XGBoost",
            model_version="1.0",
            symbol="V100",
            training_samples=1000,
            features_used='["RSI", "MACD"]',
            file_path="/test/model.pkl",
            accuracy=0.8,
            precision=0.75,
            recall=0.85,
            f1_score=0.8,
        )
        session.add(model)
        await session.flush()
        await session.refresh(model)
        print(f"   Created model: {model}")
        print(f"   __repr__: {repr(model)}")
        model_dict = model.to_dict()
        print(f"   to_dict() keys: {list(model_dict.keys())}")
        assert model.model_name == "XGBoostTest"
        assert model.accuracy == 0.8
        print("   ModelMetadata model PASSED")

        # Test 4: Create Configuration
        print("\n5. Testing Configuration model...")
        config = Configuration(
            config_key="test_config",
            config_value="test_value",
            description="Test configuration",
            category="test",
        )
        session.add(config)
        await session.flush()
        await session.refresh(config)
        print(f"   Created config: {config}")
        print(f"   __repr__: {repr(config)}")
        config_dict = config.to_dict()
        print(f"   to_dict() keys: {list(config_dict.keys())}")
        assert config.config_key == "test_config"
        print("   Configuration model PASSED")

        # Test 5: Create MarketData
        print("\n6. Testing MarketData model...")
        market_data = MarketData(
            symbol="V100",
            timeframe="M5",
            timestamp=datetime.utcnow(),
            open_price=1.0900,
            high_price=1.0910,
            low_price=1.0890,
            close_price=1.0905,
            volume=500,
        )
        session.add(market_data)
        await session.flush()
        await session.refresh(market_data)
        print(f"   Created market_data: {market_data}")
        print(f"   __repr__: {repr(market_data)}")
        md_dict = market_data.to_dict()
        print(f"   to_dict() keys: {list(md_dict.keys())}")
        assert market_data.symbol == "V100"
        print("   MarketData model PASSED")

        # Test 6: Create Signal with relationship to Trade
        print("\n7. Testing Signal model with relationship...")
        signal = Signal(
            symbol="V100",
            direction="BUY",
            confidence=0.85,
            price=1.0900,
            strategy="TestStrategy",
            trade_id=trade.id,
        )
        session.add(signal)
        await session.flush()
        await session.refresh(signal)
        print(f"   Created signal: {signal}")
        print(f"   __repr__: {repr(signal)}")
        signal_dict = signal.to_dict()
        print(f"   to_dict() keys: {list(signal_dict.keys())}")
        assert signal.symbol == "V100"
        assert signal.trade_id == trade.id
        print("   Signal model PASSED")

        # Test 7: Create SystemLog
        print("\n8. Testing SystemLog model...")
        log = SystemLog(
            level="INFO",
            message="Test log message",
            context={"test": True},
            source="test_script",
        )
        session.add(log)
        await session.flush()
        await session.refresh(log)
        print(f"   Created log: {log}")
        print(f"   __repr__: {repr(log)}")
        log_dict = log.to_dict()
        print(f"   to_dict() keys: {list(log_dict.keys())}")
        assert log.level == "INFO"
        assert log.message == "Test log message"
        print("   SystemLog model PASSED")

        # Test 8: Verify relationships work
        print("\n9. Testing Signal-Trade relationship...")
        # Query the trade with signals loaded
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(Trade)
            .options(selectinload(Trade.signals))
            .where(Trade.id == trade.id)
        )
        trade_with_signals = result.scalar_one()
        print(f"   Trade has {len(trade_with_signals.signals)} signal(s)")
        assert len(trade_with_signals.signals) == 1
        assert trade_with_signals.signals[0].id == signal.id
        print("   Relationship PASSED")

        # Test 9: Query all models
        print("\n10. Testing queries...")
        result = await session.execute(select(Trade).where(Trade.symbol == "V100"))
        trades = result.scalars().all()
        print(f"   Found {len(trades)} trade(s)")

        result = await session.execute(select(PerformanceMetrics))
        metrics = result.scalars().all()
        print(f"   Found {len(metrics)} performance metrics(s)")

        result = await session.execute(select(ModelMetadata))
        models = result.scalars().all()
        print(f"   Found {len(models)} model(s)")

        result = await session.execute(select(Configuration))
        configs = result.scalars().all()
        print(f"   Found {len(configs)} configuration(s)")

        result = await session.execute(select(MarketData))
        market_data = result.scalars().all()
        print(f"   Found {len(market_data)} market data(s)")

        result = await session.execute(select(Signal))
        signals = result.scalars().all()
        print(f"   Found {len(signals)} signal(s)")

        result = await session.execute(select(SystemLog))
        logs = result.scalars().all()
        print(f"   Found {len(logs)} log(s)")

        # Commit everything
        await session.commit()
        print("\n   All changes committed")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print("- All 7 models created successfully")
    print("- All __repr__ methods working")
    print("- All to_dict() methods working")
    print("- Signal-Trade relationship working")
    print("- Async operations working correctly")
    print("- SQLAlchemy 2.0 async models fully functional")


if __name__ == "__main__":
    try:
        asyncio.run(test_all_models())
    except Exception as e:
        print(f"\nTest FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
