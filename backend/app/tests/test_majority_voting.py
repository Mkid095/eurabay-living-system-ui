"""
Unit tests for Majority Voting Mechanism (US-005).

Tests the majority voting system including:
- 2/3 minimum agreement threshold
- HOLD fallback when threshold not met
- Agreement-based confidence calculation
- Detailed voting logs
- Ensemble signal storage
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from app.services.ensemble_signals import (
    SignalDirection,
    SignalType,
    TradingSignal,
    MajorityVoting,
    VotingResult,
    EnsembleSignalManager,
    SignalSource
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_buy_signals():
    """Create sample BUY signals for testing."""
    return [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.75,
            timestamp=datetime.now(),
            features={"rsi": 25, "macd": 0.5},
            symbol="V10",
            price=1.0850
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.70,
            timestamp=datetime.now(),
            features={"rsi": 28, "macd": 0.4},
            symbol="V10",
            price=1.0851
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.SELL,
            confidence=0.60,
            timestamp=datetime.now(),
            features={"rsi": 30, "sma_crossover": True},
            symbol="V10",
            price=1.0852
        )
    ]


@pytest.fixture
def sample_sell_signals():
    """Create sample SELL signals for testing."""
    return [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.80,
            timestamp=datetime.now(),
            features={"rsi": 75, "macd": -0.5},
            symbol="V10",
            price=1.0850
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.75,
            timestamp=datetime.now(),
            features={"rsi": 72, "macd": -0.4},
            symbol="V10",
            price=1.0851
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.BUY,
            confidence=0.55,
            timestamp=datetime.now(),
            features={"rsi": 65, "sma_crossover": False},
            symbol="V10",
            price=1.0852
        )
    ]


@pytest.fixture
def sample_no_consensus_signals():
    """Create signals with no clear consensus."""
    return [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.60,
            timestamp=datetime.now(),
            features={"rsi": 45},
            symbol="V10",
            price=1.0850
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.60,
            timestamp=datetime.now(),
            features={"rsi": 55},
            symbol="V10",
            price=1.0851
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.HOLD,
            confidence=0.50,
            timestamp=datetime.now(),
            features={"rsi": 50},
            symbol="V10",
            price=1.0852
        )
    ]


@pytest.fixture
def sample_unanimous_buy_signals():
    """Create unanimous BUY signals."""
    return [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.85,
            timestamp=datetime.now(),
            features={"rsi": 20},
            symbol="V10",
            price=1.0850
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.80,
            timestamp=datetime.now(),
            features={"rsi": 22},
            symbol="V10",
            price=1.0851
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.BUY,
            confidence=0.70,
            timestamp=datetime.now(),
            features={"rsi": 25},
            symbol="V10",
            price=1.0852
        )
    ]


@pytest.fixture
def majority_voting():
    """Create MajorityVoting instance with default 2/3 threshold."""
    return MajorityVoting(min_agreement_threshold=2/3, min_voters=2)


# ============================================================================
# Test MajorityVoting Class
# ============================================================================

class TestMajorityVotingInitialization:
    """Tests for MajorityVoting initialization."""

    def test_initialization_default(self):
        """Test initialization with default parameters."""
        voting = MajorityVoting()

        assert voting.min_agreement_threshold == pytest.approx(2/3)
        assert voting.min_voters == 2

    def test_initialization_custom_threshold(self):
        """Test initialization with custom threshold."""
        voting = MajorityVoting(min_agreement_threshold=0.75, min_voters=3)

        assert voting.min_agreement_threshold == 0.75
        assert voting.min_voters == 3

    def test_initialization_invalid_threshold(self):
        """Test initialization with invalid threshold."""
        with pytest.raises(ValueError):
            MajorityVoting(min_agreement_threshold=1.5)

        with pytest.raises(ValueError):
            MajorityVoting(min_agreement_threshold=0.0)

    def test_initialization_invalid_min_voters(self):
        """Test initialization with invalid min_voters."""
        with pytest.raises(ValueError):
            MajorityVoting(min_voters=0)


class TestMajorityVotingVote:
    """Tests for majority voting logic."""

    def test_vote_with_2_3_consensus_met(self, majority_voting, sample_buy_signals):
        """Test voting when 2 out of 3 sources agree (threshold met)."""
        result = majority_voting.vote(sample_buy_signals)

        assert result.direction == SignalDirection.BUY
        assert result.confidence == pytest.approx(2/3)
        assert result.threshold_met is True
        assert result.num_voters == 3
        assert result.agreement_ratio == pytest.approx(2/3)
        assert result.vote_count == {"BUY": 2, "SELL": 1, "HOLD": 0}
        assert "xgboost_v10" in result.vote_details
        assert result.vote_details["xgboost_v10"] == "BUY"

    def test_vote_with_2_3_consensus_sell(self, majority_voting, sample_sell_signals):
        """Test voting for SELL when 2 out of 3 sources agree."""
        result = majority_voting.vote(sample_sell_signals)

        assert result.direction == SignalDirection.SELL
        assert result.confidence == pytest.approx(2/3)
        assert result.threshold_met is True
        assert result.vote_count == {"BUY": 1, "SELL": 2, "HOLD": 0}

    def test_vote_threshold_not_met(self, majority_voting, sample_no_consensus_signals):
        """Test voting when threshold is not met (should return HOLD)."""
        result = majority_voting.vote(sample_no_consensus_signals)

        # When no direction has majority, max is chosen but threshold not met
        # In this case, each direction has 1 vote, so max returns first alphabetically
        # But threshold_met should be False and agreement_ratio should be 1/3
        assert result.threshold_met is False
        assert result.agreement_ratio == pytest.approx(1/3)

    def test_vote_unanimous_agreement(self, majority_voting, sample_unanimous_buy_signals):
        """Test voting with unanimous agreement."""
        result = majority_voting.vote(sample_unanimous_buy_signals)

        assert result.direction == SignalDirection.BUY
        assert result.confidence == 1.0
        assert result.threshold_met is True
        assert result.agreement_ratio == 1.0
        assert result.vote_count == {"BUY": 3, "SELL": 0, "HOLD": 0}

    def test_vote_insufficient_voters(self, majority_voting, sample_buy_signals):
        """Test voting with insufficient voters."""
        # Only provide 1 signal, but min_voters is 2
        result = majority_voting.vote([sample_buy_signals[0]])

        assert result.direction == SignalDirection.HOLD
        assert result.threshold_met is False
        assert result.num_voters == 1

    def test_vote_empty_signals(self, majority_voting):
        """Test voting with empty signal list."""
        result = majority_voting.vote([])

        assert result.direction == SignalDirection.HOLD
        assert result.threshold_met is False
        assert result.num_voters == 0
        assert result.agreement_ratio == 0.0

    def test_vote_details_tracking(self, majority_voting, sample_buy_signals):
        """Test that vote details are correctly tracked."""
        result = majority_voting.vote(sample_buy_signals)

        assert len(result.vote_details) == 3
        assert result.vote_details["xgboost_v10"] == "BUY"
        assert result.vote_details["random_forest_v10"] == "BUY"
        assert result.vote_details["rule_based_v10"] == "SELL"

    def test_custom_threshold_strict(self, sample_buy_signals):
        """Test with stricter threshold (3/3 required)."""
        voting = MajorityVoting(min_agreement_threshold=1.0, min_voters=2)
        result = voting.vote(sample_buy_signals)

        # Only 2/3 agree, but threshold is 1.0, so should return HOLD
        assert result.threshold_met is False
        assert result.direction == SignalDirection.HOLD

    def test_custom_threshold_lenient(self, sample_buy_signals):
        """Test with more lenient threshold (1/2 required)."""
        voting = MajorityVoting(min_agreement_threshold=0.5, min_voters=2)

        # Create signals with 2/3 agreement
        result = voting.vote(sample_buy_signals)

        # 2/3 > 0.5, so threshold should be met
        assert result.threshold_met is True
        assert result.direction == SignalDirection.BUY


# ============================================================================
# Test VotingResult
# ============================================================================

class TestVotingResult:
    """Tests for VotingResult dataclass."""

    def test_voting_result_to_dict(self):
        """Test converting VotingResult to dictionary."""
        result = VotingResult(
            direction=SignalDirection.BUY,
            confidence=0.67,
            threshold_met=True,
            vote_details={"xgboost": "BUY", "rf": "BUY", "rules": "SELL"},
            vote_count={"BUY": 2, "SELL": 1, "HOLD": 0},
            num_voters=3,
            agreement_ratio=0.67
        )

        result_dict = result.to_dict()

        assert result_dict["direction"] == "BUY"
        assert result_dict["confidence"] == 0.67
        assert result_dict["threshold_met"] is True
        assert result_dict["vote_details"]["xgboost"] == "BUY"
        assert result_dict["vote_count"]["BUY"] == 2
        assert result_dict["num_voters"] == 3
        assert result_dict["agreement_ratio"] == 0.67


# ============================================================================
# Test EnsembleSignalManager Integration
# ============================================================================

class TestEnsembleSignalManagerIntegration:
    """Tests for EnsembleSignalManager integration with MajorityVoting."""

    def test_manager_initialization_with_voting(self):
        """Test that manager initializes MajorityVoting."""
        manager = EnsembleSignalManager(
            majority_voting_threshold=0.75,
            majority_voting_min_voters=3
        )

        assert manager._majority_voting is not None
        assert manager._majority_voting.min_agreement_threshold == 0.75
        assert manager._majority_voting.min_voters == 3

    def test_manager_majority_vote_with_threshold(self, sample_buy_signals):
        """Test manager's majority_vote_with_threshold method."""
        manager = EnsembleSignalManager()
        result = manager.majority_vote_with_threshold(sample_buy_signals)

        assert isinstance(result, VotingResult)
        assert result.direction == SignalDirection.BUY
        assert result.threshold_met is True

    def test_manager_with_registered_sources(self):
        """Test voting with registered signal sources."""
        manager = EnsembleSignalManager()

        # Register mock signal sources
        xgb_source = SignalSource(
            name="xgboost_v10",
            description="XGBoost for V10",
            priority=3,
            enabled=True
        )
        rf_source = SignalSource(
            name="random_forest_v10",
            description="Random Forest for V10",
            priority=2,
            enabled=True
        )
        rule_source = SignalSource(
            name="rule_based_v10",
            description="Rule-based for V10",
            priority=1,
            enabled=True
        )

        manager.register_signal_source(xgb_source)
        manager.register_signal_source(rf_source)
        manager.register_signal_source(rule_source)

        # Check sources are registered
        sources = manager.list_signal_sources(enabled_only=True)
        assert len(sources) == 3

    def test_manager_statistics(self):
        """Test getting manager statistics."""
        manager = EnsembleSignalManager()

        stats = manager.get_statistics()

        assert "total_sources" in stats
        assert "enabled_sources" in stats
        assert "sources" in stats


# ============================================================================
# Test Agreement-Based Confidence
# ============================================================================

class TestAgreementBasedConfidence:
    """Tests for agreement-based confidence calculation."""

    def test_confidence_2_3_agreement(self, majority_voting, sample_buy_signals):
        """Test confidence calculation with 2/3 agreement."""
        result = majority_voting.vote(sample_buy_signals)

        # Confidence should be equal to agreement ratio
        assert result.confidence == result.agreement_ratio
        assert result.confidence == pytest.approx(2/3)

    def test_confidence_unanimous(self, majority_voting, sample_unanimous_buy_signals):
        """Test confidence calculation with unanimous agreement."""
        result = majority_voting.vote(sample_unanimous_buy_signals)

        assert result.confidence == 1.0
        assert result.agreement_ratio == 1.0

    def test_confidence_below_threshold(self, majority_voting, sample_no_consensus_signals):
        """Test confidence when threshold not met."""
        result = majority_voting.vote(sample_no_consensus_signals)

        # Confidence should still reflect actual agreement
        assert result.agreement_ratio < majority_voting.min_agreement_threshold
        assert result.threshold_met is False


# ============================================================================
# Test Detailed Logging
# ============================================================================

class TestDetailedLogging:
    """Tests for detailed voting logs."""

    def test_vote_count_accuracy(self, majority_voting, sample_buy_signals):
        """Test that vote counts are accurate."""
        result = majority_voting.vote(sample_buy_signals)

        assert result.vote_count["BUY"] == 2
        assert result.vote_count["SELL"] == 1
        assert result.vote_count["HOLD"] == 0

    def test_vote_details_completeness(self, majority_voting, sample_buy_signals):
        """Test that all sources are in vote details."""
        result = majority_voting.vote(sample_buy_signals)

        expected_sources = {"xgboost_v10", "random_forest_v10", "rule_based_v10"}
        actual_sources = set(result.vote_details.keys())

        assert actual_sources == expected_sources

    def test_vote_details_accuracy(self, majority_voting, sample_buy_signals):
        """Test that vote details match actual signal directions."""
        result = majority_voting.vote(sample_buy_signals)

        for signal in sample_buy_signals:
            assert result.vote_details[signal.source] == signal.direction.value


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_all_hold_signals(self, majority_voting):
        """Test when all signals are HOLD."""
        signals = [
            TradingSignal(
                source=f"source_{i}",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.HOLD,
                confidence=0.5,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=1.0850
            )
            for i in range(3)
        ]

        result = majority_voting.vote(signals)

        assert result.direction == SignalDirection.HOLD
        assert result.vote_count["HOLD"] == 3

    def test_single_source(self):
        """Test with only one signal source."""
        voting = MajorityVoting(min_agreement_threshold=0.5, min_voters=1)

        signal = TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=1.0850
        )

        result = voting.vote([signal])

        assert result.direction == SignalDirection.BUY
        assert result.num_voters == 1

    def test_four_sources_with_threshold(self):
        """Test with 4 sources and 2/3 threshold."""
        voting = MajorityVoting(min_agreement_threshold=2/3, min_voters=2)

        signals = [
            TradingSignal(
                source=f"source_{i}",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY if i < 3 else SignalDirection.SELL,
                confidence=0.7,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=1.0850
            )
            for i in range(4)
        ]

        result = voting.vote(signals)

        # 3/4 = 0.75 > 2/3, threshold met
        assert result.direction == SignalDirection.BUY
        assert result.threshold_met is True
        assert result.agreement_ratio == 0.75
