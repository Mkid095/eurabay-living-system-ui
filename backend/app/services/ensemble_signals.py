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
# Majority Voting Class
# ============================================================================

@dataclass
class VotingResult:
    """
    Result of majority voting process.

    Attributes:
        direction: The consensus direction (BUY/SELL/HOLD)
        confidence: Percentage of agreeing sources (0.0 to 1.0)
        threshold_met: Whether minimum agreement threshold was met
        vote_details: Dictionary showing how each source voted
        vote_count: Count of votes for each direction
        num_voters: Total number of sources that voted
        agreement_ratio: Ratio of agreeing sources to total sources
    """
    direction: SignalDirection
    confidence: float
    threshold_met: bool
    vote_details: Dict[str, str]
    vote_count: Dict[str, int]
    num_voters: int
    agreement_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert voting result to dictionary."""
        return {
            "direction": self.direction.value,
            "confidence": self.confidence,
            "threshold_met": self.threshold_met,
            "vote_details": self.vote_details,
            "vote_count": self.vote_count,
            "num_voters": self.num_voters,
            "agreement_ratio": self.agreement_ratio
        }


class MajorityVoting:
    """
    Implements majority voting mechanism for ensemble signals.

    This class combines signals from multiple sources using majority voting
    with a configurable minimum agreement threshold. Only returns a trading
    signal if the threshold is met, otherwise returns HOLD.

    Key Features:
    - Majority voting (2/3 threshold by default)
    - Agreement-based confidence calculation
    - Detailed voting logs for transparency
    - HOLD fallback when threshold not met

    Example:
        voting = MajorityVoting(min_agreement_threshold=2/3)

        result = voting.vote(signals)
        if result.threshold_met:
            print(f"Ensemble says: {result.direction}")
        else:
            print("No consensus, holding")

    Attributes:
        min_agreement_threshold: Minimum ratio of sources that must agree
                                 Default is 2/3 (0.67)
        min_voters: Minimum number of sources required for voting
                   Default is 2
    """

    def __init__(
        self,
        min_agreement_threshold: float = 2/3,
        min_voters: int = 2
    ):
        """
        Initialize the majority voting mechanism.

        Args:
            min_agreement_threshold: Minimum ratio of sources that must agree
                                    Range: 0.0 to 1.0
                                    Default: 2/3 (0.67) for 3-source ensemble
            min_voters: Minimum number of sources required to vote
                       Default: 2 (require at least 2 sources)

        Raises:
            ValueError: If threshold or min_voters are out of valid range
        """
        if not 0.0 < min_agreement_threshold <= 1.0:
            raise ValueError(
                f"min_agreement_threshold must be between 0 and 1, "
                f"got {min_agreement_threshold}"
            )

        if min_voters < 1:
            raise ValueError(
                f"min_voters must be at least 1, got {min_voters}"
            )

        self.min_agreement_threshold = min_agreement_threshold
        self.min_voters = min_voters
        logger.info(
            f"MajorityVoting initialized: threshold={min_agreement_threshold:.2f}, "
            f"min_voters={min_voters}"
        )

    def vote(self, signals: List[TradingSignal]) -> VotingResult:
        """
        Perform majority voting on signals from multiple sources.

        This method:
        1. Counts votes for BUY, SELL, HOLD
        2. Checks if minimum agreement threshold is met
        3. Returns ensemble signal only if threshold met
        4. Returns HOLD if no majority or threshold not met
        5. Calculates confidence as percentage of agreeing sources

        Args:
            signals: List of signals from different sources

        Returns:
            VotingResult containing the ensemble decision

        Example:
            signals = [
                TradingSignal(source="xgboost", direction=SignalDirection.BUY, ...),
                TradingSignal(source="rf", direction=SignalDirection.BUY, ...),
                TradingSignal(source="rules", direction=SignalDirection.SELL, ...)
            ]

            result = voting.vote(signals)
            # result.direction == SignalDirection.BUY
            # result.confidence == 0.67 (2/3 agreed)
            # result.threshold_met == True (2/3 >= 2/3)
        """
        num_voters = len(signals)

        # Check minimum voter requirement
        if num_voters < self.min_voters:
            logger.warning(
                f"Insufficient voters: {num_voters} < {self.min_voters}. "
                "Returning HOLD."
            )
            return self._create_hold_result(
                signals=signals,
                reason=f"Insufficient voters ({num_voters} < {self.min_voters})"
            )

        # Count votes for each direction
        vote_count: Dict[str, int] = {
            "BUY": 0,
            "SELL": 0,
            "HOLD": 0
        }

        # Track how each source voted
        vote_details: Dict[str, str] = {}

        for signal in signals:
            direction = signal.direction.value
            vote_count[direction] += 1
            vote_details[signal.source] = direction

        # Find the direction with most votes
        consensus_direction = max(vote_count, key=vote_count.get)
        consensus_votes = vote_count[consensus_direction]

        # Calculate agreement ratio
        agreement_ratio = consensus_votes / num_voters if num_voters > 0 else 0.0

        # Check if threshold is met
        threshold_met = agreement_ratio >= self.min_agreement_threshold

        # Log voting details
        logger.info(
            f"Voting results: {vote_count} | "
            f"Consensus: {consensus_direction} ({consensus_votes}/{num_voters}) | "
            f"Agreement: {agreement_ratio:.2%} | "
            f"Threshold: {self.min_agreement_threshold:.2%} | "
            f"Met: {threshold_met}"
        )

        # Log detailed votes
        for source, direction in vote_details.items():
            logger.debug(f"  {source}: {direction}")

        if threshold_met:
            # Threshold met, return ensemble signal
            confidence = agreement_ratio

            logger.info(
                f"Ensemble signal: {consensus_direction} "
                f"(confidence={confidence:.2%}, agreement={consensus_votes}/{num_voters})"
            )

            return VotingResult(
                direction=SignalDirection(consensus_direction),
                confidence=confidence,
                threshold_met=True,
                vote_details=vote_details,
                vote_count=vote_count,
                num_voters=num_voters,
                agreement_ratio=agreement_ratio
            )
        else:
            # Threshold not met, return HOLD
            logger.info(
                f"Agreement threshold not met: {agreement_ratio:.2%} < "
                f"{self.min_agreement_threshold:.2%}. Returning HOLD."
            )

            return VotingResult(
                direction=SignalDirection.HOLD,
                confidence=agreement_ratio,
                threshold_met=False,
                vote_details=vote_details,
                vote_count=vote_count,
                num_voters=num_voters,
                agreement_ratio=agreement_ratio
            )

    def _create_hold_result(
        self,
        signals: List[TradingSignal],
        reason: str
    ) -> VotingResult:
        """
        Create a HOLD result with logging.

        Args:
            signals: List of signals (for vote details)
            reason: Why HOLD is being returned

        Returns:
            VotingResult with HOLD direction
        """
        vote_details: Dict[str, str] = {
            signal.source: signal.direction.value
            for signal in signals
        }

        return VotingResult(
            direction=SignalDirection.HOLD,
            confidence=0.0,
            threshold_met=False,
            vote_details=vote_details,
            vote_count={"BUY": 0, "SELL": 0, "HOLD": 0},
            num_voters=len(signals),
            agreement_ratio=0.0
        )


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

    def __init__(
        self,
        majority_voting_threshold: float = 2/3,
        majority_voting_min_voters: int = 2,
        enable_decay_tracking: bool = True,
        max_signal_age_minutes: int = 30
    ):
        """
        Initialize the ensemble signal manager.

        Args:
            majority_voting_threshold: Minimum agreement ratio for majority voting
            majority_voting_min_voters: Minimum number of sources required
            enable_decay_tracking: Whether to enable signal decay tracking (US-008)
            max_signal_age_minutes: Maximum age for fresh signals (default: 30)
        """
        self._signal_sources: Dict[str, SignalSource] = {}
        self._signal_cache: Dict[str, List[TradingSignal]] = {}
        self._cache_ttl_seconds: int = 30  # Cache TTL for signals
        self._majority_voting = MajorityVoting(
            min_agreement_threshold=majority_voting_threshold,
            min_voters=majority_voting_min_voters
        )
        self._enable_decay_tracking = enable_decay_tracking
        self._max_signal_age_minutes = max_signal_age_minutes

        # Initialize decay tracker if enabled
        self._decay_tracker = None
        if enable_decay_tracking:
            from app.services.signal_decay_tracker import create_decay_tracker
            self._decay_tracker = create_decay_tracker(
                max_signal_age_minutes=max_signal_age_minutes
            )
            logger.info(
                f"EnsembleSignalManager initialized with decay tracking "
                f"(max_age={max_signal_age_minutes}min)"
            )
        else:
            logger.info("EnsembleSignalManager initialized (decay tracking disabled)")

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
                    # Apply decay tracking if enabled (US-008)
                    if self._enable_decay_tracking and self._decay_tracker:
                        if self._decay_tracker.should_discard_signal(signal):
                            logger.debug(
                                f"Discarding stale signal from {signal.source} "
                                f"(age > {self._max_signal_age_minutes}min)"
                            )
                            continue

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

    def majority_vote_with_threshold(
        self,
        signals: List[TradingSignal]
    ) -> VotingResult:
        """
        Perform majority voting with minimum agreement threshold.

        This is the US-005 implementation that uses the MajorityVoting class
        to combine signals with strict threshold requirements.

        Features:
        - Requires 2/3 minimum agreement threshold (configurable)
        - Returns HOLD if no majority or threshold not met
        - Confidence calculated as percentage of agreeing sources
        - Detailed logging of which sources voted how

        Args:
            signals: List of signals from different sources

        Returns:
            VotingResult containing ensemble decision

        Example:
            result = manager.majority_vote_with_threshold(signals)

            if result.threshold_met:
                # Trade the signal
                execute_trade(result.direction)
            else:
                # No consensus, wait
                logger.info("No ensemble consensus, holding")

        Note:
            This is the recommended method for US-005 compliance.
            The aggregate_signals() method is kept for backward compatibility.
        """
        return self._majority_voting.vote(signals)

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
            "decay_tracking_enabled": self._enable_decay_tracking,
            "max_signal_age_minutes": self._max_signal_age_minutes,
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

    def get_decay_tracker(self):
        """
        Get the decay tracker instance.

        Returns:
            SignalDecayTracker instance if enabled, None otherwise

        Example:
            tracker = manager.get_decay_tracker()
            if tracker:
                is_fresh = tracker.is_signal_fresh(signal)
        """
        return self._decay_tracker


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
    "VotingResult",
    "MajorityVoting",
    "EnsembleSignalManager",
    "create_ensemble_manager"
]
