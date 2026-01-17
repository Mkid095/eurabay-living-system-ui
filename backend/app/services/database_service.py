"""
Database service for EURABAY Living System.
Provides high-level CRUD operations for all models with async support.
"""
from typing import Optional, List, Type, TypeVar, Generic
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from loguru import logger

# Import models
from app.models import (
    Trade,
    PerformanceMetrics,
    ModelMetadata,
    Configuration,
    MarketData,
    Signal,
)

# Type variable for generic CRUD operations
T = TypeVar("T", bound=object)


class DatabaseService:
    """
    High-level database service providing CRUD operations for all models.
    Includes connection pooling via SQLAlchemy async engine.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize database service with a session.

        Args:
            session: Async database session
        """
        self.session = session

    # ========================================================================
    # Generic CRUD Operations
    # ========================================================================

    async def create(self, model: Type[T], **kwargs) -> T:
        """
        Create a new record.

        Args:
            model: SQLAlchemy model class
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        try:
            instance = model(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            logger.info(f"Created {model.__name__} with ID {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create {model.__name__}: {e}")
            await self.session.rollback()
            raise

    async def get_by_id(
        self,
        model: Type[T],
        record_id: int
    ) -> Optional[T]:
        """
        Get a record by ID.

        Args:
            model: SQLAlchemy model class
            record_id: Record ID

        Returns:
            Model instance or None
        """
        try:
            result = await self.session.execute(
                select(model).where(model.id == record_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get {model.__name__} by ID {record_id}: {e}")
            raise

    async def get_all(
        self,
        model: Type[T],
        limit: Optional[int] = None,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """
        Get all records matching filters.

        Args:
            model: SQLAlchemy model class
            limit: Maximum number of records to return
            offset: Number of records to skip
            **filters: Field filters

        Returns:
            List of model instances
        """
        try:
            query = select(model)

            # Apply filters
            for key, value in filters.items():
                if hasattr(model, key):
                    query = query.where(getattr(model, key) == value)

            # Apply limit and offset
            if limit:
                query = query.limit(limit)
            query = query.offset(offset)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get {model.__name__} records: {e}")
            raise

    async def update(
        self,
        model: Type[T],
        record_id: int,
        **kwargs
    ) -> Optional[T]:
        """
        Update a record by ID.

        Args:
            model: SQLAlchemy model class
            record_id: Record ID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None
        """
        try:
            # Add updated_at timestamp if model has it
            if hasattr(model, "updated_at"):
                kwargs["updated_at"] = datetime.utcnow()

            await self.session.execute(
                update(model)
                .where(model.id == record_id)
                .values(**kwargs)
            )
            await self.session.flush()

            # Return updated instance
            return await self.get_by_id(model, record_id)
        except Exception as e:
            logger.error(f"Failed to update {model.__name__} ID {record_id}: {e}")
            await self.session.rollback()
            raise

    async def delete(self, model: Type[T], record_id: int) -> bool:
        """
        Delete a record by ID.

        Args:
            model: SQLAlchemy model class
            record_id: Record ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.session.execute(
                delete(model).where(model.id == record_id)
            )
            await self.session.flush()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted {model.__name__} with ID {record_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete {model.__name__} ID {record_id}: {e}")
            await self.session.rollback()
            raise

    async def count(self, model: Type[T], **filters) -> int:
        """
        Count records matching filters.

        Args:
            model: SQLAlchemy model class
            **filters: Field filters

        Returns:
            Number of matching records
        """
        try:
            query = select(func.count(model.id))

            # Apply filters
            for key, value in filters.items():
                if hasattr(model, key):
                    query = query.where(getattr(model, key) == value)

            result = await self.session.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count {model.__name__} records: {e}")
            raise

    # ========================================================================
    # Trade Operations
    # ========================================================================

    async def create_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        lot_size: float,
        confidence: float,
        strategy_used: str,
        mt5_ticket: Optional[int] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Trade:
        """Create a new trade record."""
        return await self.create(
            Trade,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            lot_size=lot_size,
            confidence=confidence,
            strategy_used=strategy_used,
            mt5_ticket=mt5_ticket,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.utcnow(),
            status="OPEN",
        )

    async def get_open_trades(self, symbol: Optional[str] = None) -> List[Trade]:
        """Get all open trades, optionally filtered by symbol."""
        filters = {"status": "OPEN"}
        if symbol:
            filters["symbol"] = symbol
        return await self.get_all(Trade, **filters)

    async def update_trade_status(
        self,
        trade_id: int,
        status: str,
        exit_price: Optional[float] = None,
        profit_loss: Optional[float] = None,
    ) -> Optional[Trade]:
        """Update trade status and exit information."""
        update_data = {"status": status}
        if exit_price:
            update_data["exit_price"] = exit_price
            update_data["exit_time"] = datetime.utcnow()
        if profit_loss is not None:
            update_data["profit_loss"] = profit_loss

        return await self.update(Trade, trade_id, **update_data)

    async def get_trades_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: Optional[str] = None,
    ) -> List[Trade]:
        """Get trades within a date range."""
        query = select(Trade).where(
            and_(
                Trade.entry_time >= start_date,
                Trade.entry_time <= end_date,
            )
        )
        if symbol:
            query = query.where(Trade.symbol == symbol)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Performance Metrics Operations
    # ========================================================================

    async def create_performance_metrics(
        self,
        period: str,
        period_start: datetime,
        period_end: datetime,
        **metrics_data
    ) -> PerformanceMetrics:
        """Create performance metrics record."""
        return await self.create(
            PerformanceMetrics,
            period=period,
            period_start=period_start,
            period_end=period_end,
            **metrics_data
        )

    async def get_latest_metrics(self, period: str = "all_time") -> Optional[PerformanceMetrics]:
        """Get the latest performance metrics for a period."""
        result = await self.session.execute(
            select(PerformanceMetrics)
            .where(PerformanceMetrics.period == period)
            .order_by(PerformanceMetrics.period_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_metrics(self, metrics_id: int, **data) -> Optional[PerformanceMetrics]:
        """Update performance metrics."""
        return await self.update(PerformanceMetrics, metrics_id, **data)

    # ========================================================================
    # Model Metadata Operations
    # ========================================================================

    async def create_model_metadata(
        self,
        model_name: str,
        model_type: str,
        model_version: str,
        symbol: str,
        file_path: str,
        training_samples: int,
        features_used: List[str],
        **metrics
    ) -> ModelMetadata:
        """Create model metadata record."""
        import json

        return await self.create(
            ModelMetadata,
            model_name=model_name,
            model_type=model_type,
            model_version=model_version,
            symbol=symbol,
            file_path=file_path,
            training_samples=training_samples,
            features_used=json.dumps(features_used),
            **metrics
        )

    async def get_active_models(self, symbol: Optional[str] = None) -> List[ModelMetadata]:
        """Get all active models, optionally filtered by symbol."""
        filters = {"is_active": True}
        if symbol:
            filters["symbol"] = symbol
        return await self.get_all(ModelMetadata, **filters)

    async def deactivate_model(self, model_id: int) -> Optional[ModelMetadata]:
        """Deactivate a model."""
        return await self.update(ModelMetadata, model_id, is_active=False)

    async def get_latest_model(self, symbol: str, model_name: str) -> Optional[ModelMetadata]:
        """Get the latest active model for a symbol."""
        result = await self.session.execute(
            select(ModelMetadata)
            .where(
                and_(
                    ModelMetadata.symbol == symbol,
                    ModelMetadata.model_name == model_name,
                    ModelMetadata.is_active == True,
                )
            )
            .order_by(ModelMetadata.training_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # Configuration Operations
    # ========================================================================

    async def get_configuration(self, config_key: str) -> Optional[Configuration]:
        """Get configuration by key."""
        result = await self.session.execute(
            select(Configuration).where(Configuration.config_key == config_key)
        )
        return result.scalar_one_or_none()

    async def set_configuration(
        self,
        config_key: str,
        config_value: str,
        description: str,
        category: str,
        is_active: bool = True,
    ) -> Configuration:
        """Set configuration value (create or update)."""
        existing = await self.get_configuration(config_key)

        if existing:
            # Update existing
            return await self.update(
                Configuration,
                existing.id,
                config_value=config_value,
                description=description,
                category=category,
                is_active=is_active,
            )
        else:
            # Create new
            return await self.create(
                Configuration,
                config_key=config_key,
                config_value=config_value,
                description=description,
                category=category,
                is_active=is_active,
            )

    async def get_configurations_by_category(self, category: str) -> List[Configuration]:
        """Get all configurations in a category."""
        return await self.get_all(Configuration, category=category, is_active=True)

    async def get_all_configurations(self) -> dict[str, str]:
        """Get all active configurations as a dictionary."""
        configs = await self.get_all(Configuration, is_active=True)
        return {config.config_key: config.config_value for config in configs}

    # ========================================================================
    # Market Data Operations
    # ========================================================================

    async def create_market_data(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int = 0,
    ) -> MarketData:
        """Create market data record."""
        return await self.create(
            MarketData,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

    async def get_market_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
    ) -> List[MarketData]:
        """Get market data for a symbol and timeframe within date range."""
        query = select(MarketData).where(
            and_(
                MarketData.symbol == symbol,
                MarketData.timeframe == timeframe,
                MarketData.timestamp >= start_date,
                MarketData.timestamp <= end_date,
            )
        ).order_by(MarketData.timestamp.asc())

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_market_data(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> List[MarketData]:
        """Get the most recent market data for a symbol."""
        result = await self.session.execute(
            select(MarketData)
            .where(
                and_(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == timeframe,
                )
            )
            .order_by(MarketData.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def bulk_insert_market_data(self, data_list: List[dict]) -> int:
        """
        Bulk insert market data records.

        Args:
            data_list: List of dictionaries containing market data

        Returns:
            Number of records inserted
        """
        try:
            objects = [MarketData(**data) for data in data_list]
            self.session.add_all(objects)
            await self.session.flush()
            logger.info(f"Bulk inserted {len(objects)} market data records")
            return len(objects)
        except Exception as e:
            logger.error(f"Failed to bulk insert market data: {e}")
            await self.session.rollback()
            raise

    # ========================================================================
    # Signal Operations
    # ========================================================================

    async def create_signal(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        price: float,
        strategy: str,
        reasons: Optional[List[str]] = None,
    ) -> Signal:
        """Create a signal record."""
        return await self.create(
            Signal,
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            price=price,
            strategy=strategy,
            reasons=reasons or [],
            timestamp=datetime.utcnow(),
            executed=False,
        )

    async def get_recent_signals(
        self,
        symbol: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Signal]:
        """Get recent signals within the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(Signal).where(Signal.timestamp >= since)

        if symbol:
            query = query.where(Signal.symbol == symbol)

        query = query.order_by(Signal.timestamp.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_signal_executed(
        self,
        signal_id: int,
        trade_id: Optional[int] = None,
    ) -> Optional[Signal]:
        """Mark a signal as executed."""
        return await self.update(
            Signal,
            signal_id,
            executed=True,
            trade_id=trade_id,
        )

    async def get_unexecuted_signals(self, symbol: Optional[str] = None) -> List[Signal]:
        """Get all unexecuted signals."""
        filters = {"executed": False}
        if symbol:
            filters["symbol"] = symbol
        return await self.get_all(Signal, **filters)

    async def create_ensemble_signal(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        price: float,
        vote_details: dict,
        vote_count: dict,
        agreement_ratio: float,
        threshold_met: bool,
        num_voters: int,
    ) -> Signal:
        """
        Create an ensemble signal record from majority voting.

        This method stores ensemble signals generated by the MajorityVoting class,
        capturing all the voting details for analysis and audit trail.

        Args:
            symbol: Trading symbol (e.g., V10, V25)
            direction: Signal direction (BUY/SELL/HOLD)
            confidence: Agreement-based confidence (0-1)
            price: Price at signal generation
            vote_details: Dictionary of which source voted how
            vote_count: Count of votes for each direction
            agreement_ratio: Ratio of agreeing sources
            threshold_met: Whether minimum agreement threshold was met
            num_voters: Total number of sources that voted

        Returns:
            Created Signal instance

        Example:
            signal = await db_service.create_ensemble_signal(
                symbol="V10",
                direction="BUY",
                confidence=0.67,
                price=1.0850,
                vote_details={"xgboost": "BUY", "rf": "BUY", "rules": "SELL"},
                vote_count={"BUY": 2, "SELL": 1, "HOLD": 0},
                agreement_ratio=0.67,
                threshold_met=True,
                num_voters=3
            )
        """
        import json

        # Build reasons from voting details
        reasons = [
            f"Ensemble signal from {num_voters} sources",
            f"Agreement: {agreement_ratio:.1%}",
            f"Threshold met: {threshold_met}",
            f"Votes: {vote_count}",
            f"Sources: {vote_details}"
        ]

        return await self.create(
            Signal,
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            price=price,
            strategy="ensemble_majority_vote",
            reasons=reasons,
            timestamp=datetime.utcnow(),
            executed=False,
        )


# ========================================================================
# Helper Functions
# ========================================================================

async def get_db_service(session: AsyncSession) -> DatabaseService:
    """
    Get a database service instance.

    Args:
        session: Async database session

    Returns:
        DatabaseService instance
    """
    return DatabaseService(session)
