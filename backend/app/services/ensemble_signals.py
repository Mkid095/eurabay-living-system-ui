"""
Ensemble Signal System for EURABAY Living System.

This module provides the foundation for managing multiple signal sources
and coordinating their outputs through an ensemble approach.

Key Components:
- Signal schema definition
- EnsembleSignalManager class
- Signal validation and aggregation
"""

from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from app.core.logging import logger


# ============================================================================
# Signal Direction Enum
# ============================================================================

class SignalDirection(str, Enum):
    """Signal direction types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ============================================================================
# Signal Type Enum
# ============================================================================

class SignalType(str, Enum):
    """Signal generation types."""
    ML_MODEL = "ML_MODEL"  # Machine Learning model signals
    RULE_BASED = "RULE_BASED"  # Technical analysis rules
    ENSEMBLE = "ENSEMBLE"  # Combined ensemble signals


# ============================================================================
# Signal Schema
# ============================================================================

@dataclass
class TradingSignal:
    """
    Trading signal schema.

    Attributes:
        source: Signal source identifier (e.g., 'xgboost_v10', 'rule_based_rsi')
        type: Signal generation type
        direction: Trading direction (BUY/SELL/HOLD)
        confidence: Signal confidence score (0.0 to 1.0)
        timestamp: When the signal was generated
        features: Dictionary of features used for signal generation
        symbol: Trading symbol (e.g., V10, V25)
        price: Price at signal generation
        metadata: Additional signal metadata
    """
    source: str
    type: SignalType
    direction: SignalDirection
    confidence: float
    timestamp: datetime
    features: Dict[str, Any]
    symbol: str
    price: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate signal after initialization."""
        # Ensure confidence is between 0 and 1
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

        # Ensure price is positive
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary."""
        return {
            "source": self.source,
            "type": self.type.value,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "features": self.features,
            "symbol": self.symbol,
            "price": self.price,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingSignal":
        """Create signal from dictionary."""
        return cls(
            source=data["source"],
            type=SignalType(data["type"]),
            direction=SignalDirection(data["direction"]),
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            features=data["features"],
            symbol=data["symbol"],
            price=data["price"],
            metadata=data.get("metadata", {})
        )


# ============================================================================
# Signal Source Definition
# ============================================================================

@dataclass
class SignalSource:
    """
    Signal source definition.

    A signal source is a provider that generates trading signals.
    It can be an ML model, rule-based system, or external service.

    Attributes:
        name: Unique identifier for the signal source
        description: Description of the signal source
        priority: Priority for voting (higher = more weight)
        enabled: Whether the source is active
    """
    name: str
    description: str
    priority: int = 1
    enabled: bool = True
    signal_generator: Optional[Callable] = None

    def __hash__(self) -> int:
        """Make signal source hashable for set operations."""
        return hash(self.name)


# ============================================================================
# Ensemble Signal Manager
# ============================================================================

class EnsembleSignalManager:
    """
    Manages multiple signal sources and coordinates their outputs.

    This class provides the foundation for ensemble signal generation by:
    - Registering and managing signal sources
    - Fetching signals from all sources
    - Validating signal format and validity
    - Aggregating signals from multiple sources

    Example:
        manager = EnsembleSignalManager()

        # Register a signal source
        source = SignalSource(name="xgboost_v10", description="XGBoost for V10")
        manager.register_signal_source(source)

        # Fetch all signals
        signals = await manager.get_all_signals(symbol="V10")

        # Validate a signal
        is_valid = manager.validate_signal(signal)
    """

    def __init__(self):
        """Initialize the ensemble signal manager."""
        self._signal_sources: Dict[str, SignalSource] = {}
        self._signal_cache: Dict[str, List[TradingSignal]] = {}
        self._cache_ttl_seconds: int = 30  # Cache TTL for signals
        logger.info("EnsembleSignalManager initialized")

    # ========================================================================
    # Signal Source Registration
    # ========================================================================

    def register_signal_source(self, source: SignalSource) -> None:
        """
        Register a new signal source.

        Args:
            source: SignalSource instance to register

        Raises:
            ValueError: If source name already exists
        """
        if source.name in self._signal_sources:
            raise ValueError(f"Signal source '{source.name}' already registered")

        self._signal_sources[source.name] = source
        logger.info(
            f"Registered signal source: {source.name} "
            f"(priority={source.priority}, enabled={source.enabled})"
        )

    def unregister_signal_source(self, source_name: str) -> None:
        """
        Unregister a signal source.

        Args:
            source_name: Name of the source to unregister

        Raises:
            KeyError: If source name doesn't exist
        """
        if source_name not in self._signal_sources:
            raise KeyError(f"Signal source '{source_name}' not found")

        del self._signal_sources[source_name]
        logger.info(f"Unregistered signal source: {source_name}")

    def get_signal_source(self, source_name: str) -> Optional[SignalSource]:
        """
        Get a registered signal source.

        Args:
            source_name: Name of the source to retrieve

        Returns:
            SignalSource if found, None otherwise
        """
        return self._signal_sources.get(source_name)

    def list_signal_sources(self, enabled_only: bool = False) -> List[SignalSource]:
        """
        List all registered signal sources.

        Args:
            enabled_only: If True, only return enabled sources

        Returns:
            List of SignalSource instances
        """
        sources = list(self._signal_sources.values())

        if enabled_only:
            sources = [s for s in sources if s.enabled]

        # Sort by priority (descending)
        sources.sort(key=lambda x: x.priority, reverse=True)

        return sources

    def enable_signal_source(self, source_name: str) -> None:
        """
        Enable a signal source.

        Args:
            source_name: Name of the source to enable

        Raises:
            KeyError: If source name doesn't exist
        """
        if source_name not in self._signal_sources:
            raise KeyError(f"Signal source '{source_name}' not found")

        self._signal_sources[source_name].enabled = True
        logger.info(f"Enabled signal source: {source_name}")

    def disable_signal_source(self, source_name: str) -> None:
        """
        Disable a signal source.

        Args:
            source_name: Name of the source to disable

        Raises:
            KeyError: If source name doesn't exist
        """
        if source_name not in self._signal_sources:
            raise KeyError(f"Signal source '{source_name}' not found")

        self._signal_sources[source_name].enabled = False
        logger.info(f"Disabled signal source: {source_name}")

    # ========================================================================
    # Signal Generation
    # ========================================================================

    async def get_all_signals(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> List[TradingSignal]:
        """
        Fetch signals from all registered and enabled sources.

        This method calls the signal_generator function for each enabled
        signal source and aggregates the results.

        Args:
            symbol: Trading symbol to get signals for
            use_cache: Whether to use cached signals if available

        Returns:
            List of TradingSignal instances from all sources

        Example:
            signals = await manager.get_all_signals(symbol="V10")
            for signal in signals:
                print(f"{signal.source}: {signal.direction} ({signal.confidence})")
        """
        cache_key = f"{symbol}_signals"

        # Check cache first
        if use_cache and cache_key in self._signal_cache:
            logger.debug(f"Using cached signals for {symbol}")
            return self._signal_cache[cache_key]

        signals = []
        enabled_sources = self.list_signal_sources(enabled_only=True)

        logger.debug(f"Fetching signals from {len(enabled_sources)} sources for {symbol}")

        for source in enabled_sources:
            try:
                # Check if source has a signal generator
                if source.signal_generator is None:
                    logger.warning(f"Signal source '{source.name}' has no generator, skipping")
                    continue

                # Call the signal generator
                # It can be either sync or async
                if asyncio.iscoroutinefunction(source.signal_generator):
                    signal = await source.signal_generator(symbol)
                else:
                    signal = source.signal_generator(symbol)

                # Validate the signal
                if signal is not None and self.validate_signal(signal):
                    signals.append(signal)
                    logger.debug(
                        f"Received {signal.direction} signal from {signal.source} "
                        f"for {symbol} (confidence={signal.confidence:.2f})"
                    )
                else:
                    logger.warning(f"Invalid signal received from {source.name}")

            except Exception as e:
                logger.error(f"Error fetching signal from {source.name}: {e}", exc_info=True)

        # Update cache
        self._signal_cache[cache_key] = signals

        logger.info(f"Generated {len(signals)} signals for {symbol}")
        return signals

    def clear_signal_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear the signal cache.

        Args:
            symbol: If provided, only clear cache for this symbol.
                   Otherwise, clear all cache.
        """
        if symbol:
            cache_key = f"{symbol}_signals"
            if cache_key in self._signal_cache:
                del self._signal_cache[cache_key]
                logger.debug(f"Cleared signal cache for {symbol}")
        else:
            self._signal_cache.clear()
            logger.debug("Cleared all signal cache")

    # ========================================================================
    # Signal Validation
    # ========================================================================

    def validate_signal(self, signal: Any) -> bool:
        """
        Validate signal format and validity.

        Checks that the signal:
        - Is a TradingSignal instance
        - Has valid direction (BUY, SELL, HOLD)
        - Has valid confidence (0.0 to 1.0)
        - Has required fields populated
        - Has a valid timestamp

        Args:
            signal: Signal to validate

        Returns:
            True if signal is valid, False otherwise

        Example:
            signal = TradingSignal(...)
            is_valid = manager.validate_signal(signal)
        """
        # Check type
        if not isinstance(signal, TradingSignal):
            logger.warning(f"Signal validation failed: not a TradingSignal instance")
            return False

        # Check required fields
        if not signal.source:
            logger.warning("Signal validation failed: missing source")
            return False

        if not signal.symbol:
            logger.warning("Signal validation failed: missing symbol")
            return False

        # Check direction is valid
        if signal.direction not in SignalDirection:
            logger.warning(f"Signal validation failed: invalid direction {signal.direction}")
            return False

        # Check confidence range
        if not 0.0 <= signal.confidence <= 1.0:
            logger.warning(f"Signal validation failed: confidence out of range {signal.confidence}")
            return False

        # Check price is positive
        if signal.price <= 0:
            logger.warning(f"Signal validation failed: invalid price {signal.price}")
            return False

        # Check timestamp is reasonable (not too far in future)
        if signal.timestamp > datetime.now():
            logger.warning(f"Signal validation failed: timestamp in the future")
            return False

        # Check signal freshness (not too old)
        signal_age = (datetime.now() - signal.timestamp).total_seconds()
        max_age_seconds = 3600  # 1 hour max age
        if signal_age > max_age_seconds:
            logger.warning(f"Signal validation failed: signal too old ({signal_age}s)")
            return False

        logger.debug(f"Signal validated successfully: {signal.source}")
        return True

    # ========================================================================
    # Signal Aggregation
    # ========================================================================

    def aggregate_signals(
        self,
        signals: List[TradingSignal],
        method: str = "majority_vote"
    ) -> Dict[str, Any]:
        """
        Aggregate signals from multiple sources.

        This method combines signals from different sources using various
        aggregation methods to produce a consensus decision.

        Args:
            signals: List of signals to aggregate
            method: Aggregation method ('majority_vote', 'weighted', 'unanimous')

        Returns:
            Dictionary containing aggregation results

        Example:
            result = manager.aggregate_signals(signals, method="majority_vote")
            print(result["direction"])  # Consensus direction
            print(result["confidence"])  # Consensus confidence
        """
        if not signals:
            return {
                "direction": SignalDirection.HOLD,
                "confidence": 0.0,
                "agreement": 0.0,
                "vote_count": {"BUY": 0, "SELL": 0, "HOLD": 0},
                "num_signals": 0
            }

        # Count votes
        vote_count = {"BUY": 0, "SELL": 0, "HOLD": 0}
        total_confidence = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

        for signal in signals:
            direction = signal.direction.value
            vote_count[direction] += 1
            total_confidence[direction] += signal.confidence

        # Calculate consensus
        num_signals = len(signals)

        if method == "majority_vote":
            # Simple majority vote
            consensus_direction = max(vote_count, key=vote_count.get)
            consensus_votes = vote_count[consensus_direction]
            agreement = consensus_votes / num_signals if num_signals > 0 else 0.0

            # Average confidence for consensus direction
            if vote_count[consensus_direction] > 0:
                avg_confidence = total_confidence[consensus_direction] / vote_count[consensus_direction]
            else:
                avg_confidence = 0.0

        elif method == "weighted":
            # Weighted by signal source priority (not implemented yet)
            # For now, fall back to majority vote
            consensus_direction = max(vote_count, key=vote_count.get)
            consensus_votes = vote_count[consensus_direction]
            agreement = consensus_votes / num_signals if num_signals > 0 else 0.0
            avg_confidence = total_confidence[consensus_direction] / vote_count[consensus_direction] if vote_count[consensus_direction] > 0 else 0.0

        elif method == "unanimous":
            # Only return signal if all agree
            if all(v == num_signals for v in vote_count.values() if v > 0):
                consensus_direction = max(vote_count, key=vote_count.get)
                agreement = 1.0
                avg_confidence = total_confidence[consensus_direction] / num_signals
            else:
                consensus_direction = SignalDirection.HOLD
                agreement = 0.0
                avg_confidence = 0.0

        else:
            raise ValueError(f"Unknown aggregation method: {method}")

        result = {
            "direction": SignalDirection(consensus_direction),
            "confidence": avg_confidence,
            "agreement": agreement,
            "vote_count": vote_count,
            "num_signals": num_signals
        }

        logger.info(
            f"Aggregated {num_signals} signals: {consensus_direction} "
            f"(confidence={avg_confidence:.2f}, agreement={agreement:.2f})"
        )

        return result

    # ========================================================================
    # Statistics and Monitoring
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get ensemble manager statistics.

        Returns:
            Dictionary containing manager statistics
        """
        enabled_sources = self.list_signal_sources(enabled_only=True)

        return {
            "total_sources": len(self._signal_sources),
            "enabled_sources": len(enabled_sources),
            "disabled_sources": len(self._signal_sources) - len(enabled_sources),
            "cached_signals": len(self._signal_cache),
            "sources": [
                {
                    "name": s.name,
                    "description": s.description,
                    "priority": s.priority,
                    "enabled": s.enabled
                }
                for s in self._signal_sources.values()
            ]
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_ensemble_manager() -> EnsembleSignalManager:
    """
    Create and configure an ensemble signal manager.

    Returns:
        Configured EnsembleSignalManager instance
    """
    manager = EnsembleSignalManager()
    logger.info("Created new EnsembleSignalManager")
    return manager


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "SignalDirection",
    "SignalType",
    "TradingSignal",
    "SignalSource",
    "EnsembleSignalManager",
    "create_ensemble_manager"
]
