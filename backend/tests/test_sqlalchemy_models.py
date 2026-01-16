"""
Test suite for SQLAlchemy async models.
Tests all models for creation, relationships, and serialization.
"""
import asyncio
import sys
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import AsyncSessionLocal, init_db, drop_all_tables
from app.models.models import (
    Trade,
    PerformanceMetrics,
    ModelMetadata,
    Configuration,
    MarketData,
    Signal,
    SystemLog,
)


async def get_session() -> AsyncSession:
    """Get a database session for testing."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_trade_model():
    """Test Trade model creation and querying."""
    print("\n=== Testing Trade Model ===")

    async for session in get_session():
        # Create a test trade
        trade = Trade(
            mt5_ticket=12345,
            symbol="V75",
            direction="BUY",
            entry_price=1.0850,
            lot_size=0.01,
            confidence=0.85,
            strategy_used="TrendFollowing",
            stop_loss=1.0800,
            take_profit=1.0900,
            status="OPEN",
        )

        session.add(trade)
        await session.commit()
        await session.refresh(trade)

        print(f"Created trade: {trade}")

        # Test __repr__
        repr_str = repr(trade)
        print(f"Repr: {repr_str}")
        assert "Trade" in repr_str
        assert "V75" in repr_str

        # Test to_dict()
        trade_dict = trade.to_dict()
        print(f"Dict keys: {list(trade_dict.keys())}")
        assert trade_dict["symbol"] == "V75"
        assert trade_dict["direction"] == "BUY"
        assert trade_dict["status"] == "OPEN"
        assert "entry_time" in trade_dict

        # Query the trade
        result = await session.execute(select(Trade).where(Trade.symbol == "V75"))
        fetched_trade = result.scalar_one()
        assert fetched_trade.id == trade.id
        assert fetched_trade.symbol == "V75"

        print("Trade model test PASSED")


@pytest.mark.asyncio
async def test_performance_metrics_model():
    """Test PerformanceMetrics model creation and querying."""
    print("\n=== Testing PerformanceMetrics Model ===")

    async for session in get_session():
        # Create test metrics
        metrics = PerformanceMetrics(
            period="daily",
            period_start=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow(),
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            total_profit=500.0,
            total_loss=200.0,
            profit_factor=2.5,
            average_win=83.33,
            average_loss=50.0,
            max_drawdown=100.0,
            max_drawdown_pct=5.0,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            calmar_ratio=3.0,
            equity_curve={"data": [1000, 1100, 1050, 1200]},
        )

        session.add(metrics)
        await session.commit()
        await session.refresh(metrics)

        print(f"Created metrics: {metrics}")

        # Test __repr__
        repr_str = repr(metrics)
        print(f"Repr: {repr_str}")
        assert "PerformanceMetrics" in repr_str
        assert "daily" in repr_str

        # Test to_dict()
        metrics_dict = metrics.to_dict()
        print(f"Dict keys: {list(metrics_dict.keys())}")
        assert metrics_dict["period"] == "daily"
        assert metrics_dict["win_rate"] == 60.0
        assert metrics_dict["profit_factor"] == 2.5
        assert "equity_curve" in metrics_dict

        # Query the metrics
        result = await session.execute(
            select(PerformanceMetrics).where(PerformanceMetrics.period == "daily")
        )
        fetched_metrics = result.scalar_one()
        assert fetched_metrics.id == metrics.id
        assert fetched_metrics.win_rate == 60.0

        print("PerformanceMetrics model test PASSED")


@pytest.mark.asyncio
async def test_model_metadata_model():
    """Test ModelMetadata model creation and querying."""
    print("\n=== Testing ModelMetadata Model ===")

    async for session in get_session():
        # Create test model metadata
        model = ModelMetadata(
            model_name="XGBoostClassifier",
            model_type="XGBoost",
            model_version="1.0.0",
            symbol="V75",
            training_samples=10000,
            features_used='["RSI", "MACD", "BB", "ATR"]',
            file_path="/models/v75_xgboost_v1.pkl",
            accuracy=0.75,
            precision=0.73,
            recall=0.78,
            f1_score=0.75,
            is_active=True,
        )

        session.add(model)
        await session.commit()
        await session.refresh(model)

        print(f"Created model: {model}")

        # Test __repr__
        repr_str = repr(model)
        print(f"Repr: {repr_str}")
        assert "ModelMetadata" in repr_str
        assert "XGBoostClassifier" in repr_str

        # Test to_dict()
        model_dict = model.to_dict()
        print(f"Dict keys: {list(model_dict.keys())}")
        assert model_dict["model_name"] == "XGBoostClassifier"
        assert model_dict["accuracy"] == 0.75
        assert model_dict["is_active"] is True

        # Query the model
        result = await session.execute(
            select(ModelMetadata).where(ModelMetadata.model_name == "XGBoostClassifier")
        )
        fetched_model = result.scalar_one()
        assert fetched_model.id == model.id
        assert fetched_model.accuracy == 0.75

        print("ModelMetadata model test PASSED")


@pytest.mark.asyncio
async def test_configuration_model():
    """Test Configuration model creation and querying."""
    print("\n=== Testing Configuration Model ===")

    async for session in get_session():
        # Create test configuration
        config = Configuration(
            config_key="max_position_size",
            config_value="0.1",
            description="Maximum position size in lots",
            category="risk",
            is_active=True,
        )

        session.add(config)
        await session.commit()
        await session.refresh(config)

        print(f"Created config: {config}")

        # Test __repr__
        repr_str = repr(config)
        print(f"Repr: {repr_str}")
        assert "Configuration" in repr_str
        assert "max_position_size" in repr_str

        # Test to_dict()
        config_dict = config.to_dict()
        print(f"Dict keys: {list(config_dict.keys())}")
        assert config_dict["config_key"] == "max_position_size"
        assert config_dict["config_value"] == "0.1"
        assert config_dict["category"] == "risk"

        # Query the config
        result = await session.execute(
            select(Configuration).where(Configuration.config_key == "max_position_size")
        )
        fetched_config = result.scalar_one()
        assert fetched_config.id == config.id
        assert fetched_config.config_value == "0.1"

        print("Configuration model test PASSED")


@pytest.mark.asyncio
async def test_market_data_model():
    """Test MarketData model creation and querying."""
    print("\n=== Testing MarketData Model ===")

    async for session in get_session():
        # Create test market data
        market_data = MarketData(
            symbol="V75",
            timeframe="M5",
            timestamp=datetime.utcnow(),
            open_price=1.0850,
            high_price=1.0860,
            low_price=1.0840,
            close_price=1.0855,
            volume=1000,
        )

        session.add(market_data)
        await session.commit()
        await session.refresh(market_data)

        print(f"Created market_data: {market_data}")

        # Test __repr__
        repr_str = repr(market_data)
        print(f"Repr: {repr_str}")
        assert "MarketData" in repr_str
        assert "V75" in repr_str

        # Test to_dict()
        md_dict = market_data.to_dict()
        print(f"Dict keys: {list(md_dict.keys())}")
        assert md_dict["symbol"] == "V75"
        assert md_dict["timeframe"] == "M5"
        assert md_dict["close_price"] == 1.0855

        # Query the market data
        result = await session.execute(
            select(MarketData).where(MarketData.symbol == "V75")
        )
        fetched_md = result.scalar_one()
        assert fetched_md.id == market_data.id
        assert fetched_md.close_price == 1.0855

        print("MarketData model test PASSED")


@pytest.mark.asyncio
async def test_signal_model_with_relationship():
    """Test Signal model with relationship to Trade."""
    print("\n=== Testing Signal Model with Relationship ===")

    async for session in get_session():
        # First create a trade
        trade = Trade(
            mt5_ticket=67890,
            symbol="V50",
            direction="SELL",
            entry_price=1.0900,
            lot_size=0.02,
            confidence=0.90,
            strategy_used="ReversalStrategy",
            status="OPEN",
        )

        session.add(trade)
        await session.flush()  # Get the trade ID without committing

        # Create a signal linked to the trade
        signal = Signal(
            symbol="V50",
            direction="SELL",
            confidence=0.90,
            price=1.0900,
            strategy="ReversalStrategy",
            reasons={"rsi_overbought": True, "divergence": True},
            executed=True,
            trade_id=trade.id,
        )

        session.add(signal)
        await session.commit()
        await session.refresh(trade)
        await session.refresh(signal)

        print(f"Created trade: {trade}")
        print(f"Created signal: {signal}")

        # Test relationship from Signal to Trade
        print(f"Signal's trade: {signal.trade}")
        assert signal.trade is not None
        assert signal.trade.symbol == "V50"

        # Test relationship from Trade to Signal
        print(f"Trade's signals: {trade.signals}")
        assert len(trade.signals) == 1
        assert trade.signals[0].id == signal.id

        # Test __repr__
        repr_str = repr(signal)
        print(f"Repr: {repr_str}")
        assert "Signal" in repr_str
        assert "V50" in repr_str

        # Test to_dict()
        signal_dict = signal.to_dict()
        print(f"Dict keys: {list(signal_dict.keys())}")
        assert signal_dict["symbol"] == "V50"
        assert signal_dict["direction"] == "SELL"
        assert signal_dict["executed"] is True
        assert signal_dict["trade_id"] == trade.id

        # Query the signal
        result = await session.execute(
            select(Signal).where(Signal.symbol == "V50")
        )
        fetched_signal = result.scalar_one()
        assert fetched_signal.id == signal.id
        assert fetched_signal.trade_id == trade.id

        print("Signal model with relationship test PASSED")


@pytest.mark.asyncio
async def test_system_log_model():
    """Test SystemLog model creation and querying."""
    print("\n=== Testing SystemLog Model ===")

    async for session in get_session():
        # Create test system log
        log = SystemLog(
            level="INFO",
            message="System started successfully",
            context={"startup_time": 1.5, "version": "1.0.0"},
            source="SystemInitializer",
        )

        session.add(log)
        await session.commit()
        await session.refresh(log)

        print(f"Created log: {log}")

        # Test __repr__
        repr_str = repr(log)
        print(f"Repr: {repr_str}")
        assert "SystemLog" in repr_str
        assert "INFO" in repr_str

        # Test to_dict()
        log_dict = log.to_dict()
        print(f"Dict keys: {list(log_dict.keys())}")
        assert log_dict["level"] == "INFO"
        assert log_dict["message"] == "System started successfully"
        assert log_dict["source"] == "SystemInitializer"
        assert log_dict["context"] is not None

        # Query the log
        result = await session.execute(
            select(SystemLog).where(SystemLog.level == "INFO")
        )
        fetched_log = result.scalar_one()
        assert fetched_log.id == log.id
        assert fetched_log.message == "System started successfully"

        print("SystemLog model test PASSED")


@pytest.mark.asyncio
async def test_all_models_together():
    """Test all models working together."""
    print("\n=== Testing All Models Together ===")

    async for session in get_session():
        # Count all models
        trade_count = await session.execute(select(Trade))
        trade_count = len(trade_count.scalars().all())

        metrics_count = await session.execute(select(PerformanceMetrics))
        metrics_count = len(metrics_count.scalars().all())

        model_count = await session.execute(select(ModelMetadata))
        model_count = len(model_count.scalars().all())

        config_count = await session.execute(select(Configuration))
        config_count = len(config_count.scalars().all())

        md_count = await session.execute(select(MarketData))
        md_count = len(md_count.scalars().all())

        signal_count = await session.execute(select(Signal))
        signal_count = len(signal_count.scalars().all())

        log_count = await session.execute(select(SystemLog))
        log_count = len(log_count.scalars().all())

        print(f"Total trades: {trade_count}")
        print(f"Total performance metrics: {metrics_count}")
        print(f"Total models: {model_count}")
        print(f"Total configurations: {config_count}")
        print(f"Total market data: {md_count}")
        print(f"Total signals: {signal_count}")
        print(f"Total system logs: {log_count}")

        assert trade_count > 0, "No trades found"
        assert metrics_count > 0, "No performance metrics found"
        assert model_count > 0, "No models found"
        assert config_count > 0, "No configurations found"
        assert md_count > 0, "No market data found"
        assert signal_count > 0, "No signals found"
        assert log_count > 0, "No system logs found"

        print("All models together test PASSED")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("SQLAlchemy Async Models Test Suite")
    print("=" * 60)

    try:
        # Initialize database
        print("\nInitializing database...")
        await init_db()
        print("Database initialized successfully")

        # Run all tests
        await test_trade_model()
        await test_performance_metrics_model()
        await test_model_metadata_model()
        await test_configuration_model()
        await test_market_data_model()
        await test_signal_model_with_relationship()
        await test_system_log_model()
        await test_all_models_together()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\nTest FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
