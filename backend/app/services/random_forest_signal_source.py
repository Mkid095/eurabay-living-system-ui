"""
Random Forest Signal Source for EURABAY Living System.

This module implements a Random Forest-based machine learning signal source for trading.
It trains models on historical data with technical features and generates trading signals
with probability estimates and confidence scores.

Features:
- Random Forest binary classification model (100 trees)
- Training on last 6 months of historical data
- Technical features: RSI, MACD, ATR, moving averages, price momentum, volume
- Probability-based signal generation (BUY/SELL/HOLD)
- Confidence scores from tree agreement (voting)
- Feature importance tracking
- Model persistence and versioning
- Database storage for predictions
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from app.core.logging import logger
from app.services.feature_engineering import FeatureEngineering, FeatureConfig
from app.services.ensemble_signals import TradingSignal, SignalDirection, SignalType


@dataclass
class RandomForestConfig:
    """Configuration for Random Forest signal source."""

    # Model parameters
    N_ESTIMATORS: int = 100  # Number of trees in the forest
    MAX_DEPTH: int = 10  # Maximum depth of trees
    MIN_SAMPLES_SPLIT: int = 2  # Minimum samples required to split
    MIN_SAMPLES_LEAF: int = 1  # Minimum samples required at leaf node
    MAX_FEATURES: str = "sqrt"  # Number of features to consider for best split

    # Training parameters
    TRAINING_PERIOD_MONTHS: int = 6
    TEST_SIZE: float = 0.2
    RANDOM_STATE: int = 42
    N_JOBS: int = -1  # Use all available cores

    # Signal thresholds
    BUY_THRESHOLD: float = 0.6
    SELL_THRESHOLD: float = 0.6

    # Feature selection
    FEATURE_COLUMNS: List[str] = field(default_factory=list)

    # Model storage
    MODEL_DIR: str = "models"
    MODEL_VERSION_PREFIX: str = "rf_v1"


@dataclass
class RandomForestPredictionResult:
    """Result of a Random Forest model prediction."""

    probability_buy: float
    probability_sell: float
    probability_hold: float
    predicted_direction: SignalDirection
    confidence: float  # Based on tree agreement
    tree_agreement: float  # Percentage of trees agreeing with prediction
    features: Dict[str, float]
    timestamp: datetime


class RandomForestSignalSource:
    """
    Random Forest-based signal source for trading.

    This class implements a Random Forest classification model that generates
    trading signals based on technical features. It supports training, prediction,
    feature importance tracking, and model persistence.

    The Random Forest uses 100 trees and generates predictions through voting,
    where confidence is derived from the agreement between trees.

    Example:
        source = RandomForestSignalSource(symbol="V10")
        await source.initialize()
        signal = await source.predict()
    """

    def __init__(
        self,
        symbol: str,
        config: Optional[RandomForestConfig] = None,
        feature_engine: Optional[FeatureEngineering] = None
    ):
        """
        Initialize Random Forest signal source.

        Args:
            symbol: Trading symbol (e.g., V10, V25, V50, V75, V100)
            config: Random Forest configuration (uses defaults if not provided)
            feature_engine: Feature engineering instance (creates new if not provided)
        """
        self.symbol = symbol
        self.config = config or RandomForestConfig()
        self.feature_engine = feature_engine or FeatureEngineering()

        # Model storage
        self.model: Optional[RandomForestClassifier] = None
        self.feature_importance: Dict[str, float] = {}
        self.model_version: str = ""
        self.training_samples: int = 0
        self.model_metrics: Dict[str, float] = {}

        # Model file path
        self.model_dir = Path(self.config.MODEL_DIR)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_file = self.model_dir / f"{self.config.MODEL_VERSION_PREFIX}_{self.symbol}.pkl"

        # Status flags
        self._is_trained: bool = False
        self._is_initialized: bool = False

        logger.info(
            f"RandomForestSignalSource initialized for {symbol} "
            f"(n_estimators={self.config.N_ESTIMATORS}, "
            f"thresholds: BUY={self.config.BUY_THRESHOLD}, "
            f"SELL={self.config.SELL_THRESHOLD})"
        )

    # ========================================================================
    # Initialization and Training
    # ========================================================================

    async def initialize(
        self,
        historical_data: Optional[pd.DataFrame] = None,
        force_retrain: bool = False
    ) -> None:
        """
        Initialize the signal source.

        Loads existing model or trains a new one if needed.

        Args:
            historical_data: Historical OHLCV data for training (None = use cached)
            force_retrain: Force retraining even if model exists
        """
        if self._is_initialized and not force_retrain:
            logger.debug(f"RandomForestSignalSource for {self.symbol} already initialized")
            return

        # Try to load existing model
        if not force_retrain and self._load_model():
            self._is_initialized = True
            self._is_trained = True
            logger.info(f"Loaded existing Random Forest model for {self.symbol}")
            return

        # Train new model if historical data is provided
        if historical_data is not None:
            await self.train(historical_data)
            self._is_initialized = True
            logger.info(f"Trained new Random Forest model for {self.symbol}")
        else:
            logger.warning(
                f"No historical data provided for {self.symbol}, "
                f"model not trained. Call train() manually."
            )

    async def train(
        self,
        historical_data: pd.DataFrame,
        target_column: str = "target"
    ) -> Dict[str, float]:
        """
        Train Random Forest model on historical data.

        Args:
            historical_data: DataFrame with OHLCV data (must contain required columns)
            target_column: Name of target column (if pre-computed)

        Returns:
            Dictionary with training metrics (accuracy, precision, recall, f1)

        Raises:
            ValueError: If historical data is invalid or missing required columns
        """
        logger.info(f"Starting Random Forest model training for {self.symbol}")

        # Validate input data
        if historical_data.empty:
            raise ValueError("Historical data is empty")

        required_cols = ["open", "high", "low", "close"]
        missing_cols = [col for col in required_cols if col not in historical_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Limit to training period
        training_cutoff = datetime.now() - timedelta(days=30 * self.config.TRAINING_PERIOD_MONTHS)
        if "timestamp" in historical_data.columns:
            historical_data = historical_data[
                historical_data["timestamp"] >= training_cutoff
            ].copy()

        logger.info(f"Training on {len(historical_data)} samples from last {self.config.TRAINING_PERIOD_MONTHS} months")

        # Generate features
        df_with_features = self.feature_engine.generate_features(
            historical_data,
            self.symbol,
            feature_types=["returns", "rsi", "macd", "atr", "sma", "ema", "lag", "rolling"]
        )

        # Calculate target if not provided
        if target_column not in df_with_features.columns:
            df_with_features = self._calculate_target(df_with_features)

        # Prepare features and target
        X, y = self._prepare_training_data(df_with_features, target_column)

        if X is None or y is None:
            raise ValueError("Failed to prepare training data")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=self.config.TEST_SIZE,
            random_state=self.config.RANDOM_STATE,
            stratify=y
        )

        logger.info(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples")

        # Train Random Forest model
        self.model = RandomForestClassifier(
            n_estimators=self.config.N_ESTIMATORS,
            max_depth=self.config.MAX_DEPTH,
            min_samples_split=self.config.MIN_SAMPLES_SPLIT,
            min_samples_leaf=self.config.MIN_SAMPLES_LEAF,
            max_features=self.config.MAX_FEATURES,
            random_state=self.config.RANDOM_STATE,
            n_jobs=self.config.N_JOBS,
            verbose=0
        )

        self.model.fit(X_train, y_train)

        # Calculate metrics
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, average="weighted", zero_division=0),
            "recall": recall_score(y_test, y_pred, average="weighted", zero_division=0),
            "f1_score": f1_score(y_test, y_pred, average="weighted", zero_division=0)
        }

        # Store feature importance
        self.feature_importance = dict(zip(
            X.columns,
            self.model.feature_importances_.tolist()
        ))

        # Sort by importance
        self.feature_importance = dict(
            sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)
        )

        # Store metadata
        self.training_samples = len(X_train)
        self.model_metrics = metrics
        self.model_version = f"{self.config.MODEL_VERSION_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._is_trained = True
        self._is_initialized = True

        # Save model
        self._save_model()

        logger.info(
            f"Random Forest model trained for {self.symbol}: "
            f"accuracy={metrics['accuracy']:.3f}, "
            f"f1={metrics['f1_score']:.3f}, "
            f"n_trees={self.config.N_ESTIMATORS}"
        )

        return metrics

    def _calculate_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate target variable for training.

        Target is based on future price movement:
        - 1 (BUY): Price increases by more than 0.1% in next 5 periods
        - 0 (HOLD): Price change is within +/- 0.1% in next 5 periods
        - -1 (SELL): Price decreases by more than 0.1% in next 5 periods

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with target column added
        """
        # Calculate future returns
        future_return = df["close"].shift(-5) / df["close"] - 1

        # Create target: 1=BUY, 0=HOLD, -1=SELL
        # Note: Random Forest requires labels 0, 1, 2 for multi-class
        # We'll map: -1 (SELL) -> 0, 0 (HOLD) -> 1, 1 (BUY) -> 2
        target = pd.Series(1, index=df.index)  # Default to HOLD

        threshold = 0.001  # 0.1% threshold
        target.loc[future_return > threshold] = 2  # BUY
        target.loc[future_return < -threshold] = 0  # SELL

        df["target"] = target

        # Remove last 5 rows (no future data)
        df = df.iloc[:-5].copy()

        return df

    def _prepare_training_data(
        self,
        df: pd.DataFrame,
        target_column: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.Series]]:
        """
        Prepare features and target for training.

        Args:
            df: DataFrame with features
            target_column: Name of target column

        Returns:
            Tuple of (features DataFrame, target Series) or (None, None) if failed
        """
        # Define feature columns to use (same as XGBoost for consistency)
        feature_cols = [
            # Price-based features
            "return_1", "return_5", "return_10", "return_20",
            "log_return_1", "log_return_5", "log_return_10", "log_return_20",
            "price_change_1", "price_change_5", "price_change_10", "price_change_20",
            "price_rel_sma_5", "price_rel_sma_10", "price_rel_sma_20",
            "roc_1", "roc_3", "roc_5", "roc_10", "roc_20",

            # RSI
            "rsi", "rsi_overbought", "rsi_oversold",

            # MACD
            "macd", "macd_signal", "macd_hist", "macd_bullish",

            # ATR (volatility)
            "atr", "atr_ratio", "atr_7", "atr_14", "atr_21",

            # Moving averages
            "sma_5", "sma_10", "sma_20", "sma_50",
            "ema_5", "ema_10", "ema_20", "ema_50",
            "sma_cross_short_medium", "sma_cross_medium_long",
            "price_above_sma_short", "price_above_sma_long",

            # Rolling statistics
            "std_5", "std_10", "std_20", "std_50",
            "rolling_mean_5", "rolling_mean_10", "rolling_mean_20",
        ]

        # Filter to available columns
        available_features = [col for col in feature_cols if col in df.columns]

        if not available_features:
            logger.error("No features available for training")
            return None, None

        # Store selected features
        self.config.FEATURE_COLUMNS = available_features

        # Drop rows with missing values
        df_clean = df[available_features + [target_column]].dropna()

        if len(df_clean) < 100:
            logger.error(f"Insufficient data after cleaning: {len(df_clean)} samples")
            return None, None

        X = df_clean[available_features]
        y = df_clean[target_column]

        logger.info(f"Using {len(available_features)} features for {len(X)} training samples")

        return X, y

    # ========================================================================
    # Prediction
    # ========================================================================

    async def predict(
        self,
        current_data: Optional[pd.DataFrame] = None
    ) -> Optional[TradingSignal]:
        """
        Generate trading signal based on current market data.

        Uses Random Forest voting from 100 trees to generate prediction.
        Confidence is based on the agreement between trees.

        Args:
            current_data: Current market data (optional if using cached features)

        Returns:
            TradingSignal or None if prediction fails
        """
        if not self._is_trained or self.model is None:
            logger.error(f"Model not trained for {self.symbol}, cannot predict")
            return None

        try:
            # Generate prediction
            prediction = await self._generate_prediction(current_data)

            if prediction is None:
                return None

            # Create trading signal
            signal = TradingSignal(
                source=f"random_forest_{self.symbol}",
                type=SignalType.ML_MODEL,
                direction=prediction.predicted_direction,
                confidence=prediction.confidence,
                timestamp=prediction.timestamp,
                features=prediction.features,
                symbol=self.symbol,
                price=current_data["close"].iloc[-1] if current_data is not None else 0.0,
                metadata={
                    "model_version": self.model_version,
                    "n_estimators": self.config.N_ESTIMATORS,
                    "tree_agreement": prediction.tree_agreement,
                    "probabilities": {
                        "BUY": prediction.probability_buy,
                        "SELL": prediction.probability_sell,
                        "HOLD": prediction.probability_hold
                    },
                    "training_samples": self.training_samples,
                    "feature_importance": dict(list(self.feature_importance.items())[:10])  # Top 10
                }
            )

            logger.info(
                f"Random Forest signal for {self.symbol}: {signal.direction} "
                f"(confidence={signal.confidence:.2f}, "
                f"tree_agreement={prediction.tree_agreement:.2f}, "
                f"prob_buy={prediction.probability_buy:.2f}, "
                f"prob_sell={prediction.probability_sell:.2f})"
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating prediction for {self.symbol}: {e}", exc_info=True)
            return None

    async def _generate_prediction(
        self,
        current_data: Optional[pd.DataFrame] = None
    ) -> Optional[RandomForestPredictionResult]:
        """
        Generate raw prediction from Random Forest model.

        Args:
            current_data: Current market data

        Returns:
            RandomForestPredictionResult or None if failed
        """
        if current_data is None:
            logger.warning("No current data provided for prediction")
            return None

        # Validate we have enough data
        min_required = 200  # Minimum samples for feature calculation
        if len(current_data) < min_required:
            logger.error(f"Insufficient data for prediction: {len(current_data)} < {min_required}")
            return None

        # Generate features
        try:
            df_with_features = self.feature_engine.generate_features(
                current_data,
                self.symbol,
                feature_types=["returns", "rsi", "macd", "atr", "sma", "ema", "lag", "rolling"]
            )
        except Exception as e:
            logger.error(f"Error generating features: {e}")
            return None

        # Select feature columns matching training data
        if not self.config.FEATURE_COLUMNS:
            logger.error("No feature columns configured")
            return None

        # Get only the features used during training
        missing_features = set(self.config.FEATURE_COLUMNS) - set(df_with_features.columns)
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")

        available_features = [col for col in self.config.FEATURE_COLUMNS if col in df_with_features.columns]

        if not available_features:
            logger.error("No features available for prediction")
            return None

        # Get the latest row (most recent data)
        latest_row = df_with_features.iloc[[-1]]
        X = latest_row[available_features]

        # Check for NaN values
        if X.isna().any().any():
            logger.warning("Features contain NaN values, filling with zeros")
            X = X.fillna(0)

        # Generate prediction probabilities using voting from trees
        try:
            # Get probabilities from each tree and aggregate
            probabilities = self.model.predict_proba(X)[0]

            # Map probabilities: [0]=SELL, [1]=HOLD, [2]=BUY
            prob_sell = probabilities[0]
            prob_hold = probabilities[1]
            prob_buy = probabilities[2]

            # Calculate tree agreement (confidence from voting)
            # Get predictions from individual trees
            tree_predictions = []
            for tree in self.model.estimators_:
                tree_pred = tree.predict_proba(X)[0]
                tree_predictions.append(tree_pred)

            tree_predictions = np.array(tree_predictions)
            avg_tree_predictions = np.mean(tree_predictions, axis=0)

            # Tree agreement is the maximum average probability
            tree_agreement = float(np.max(avg_tree_predictions))

            # Determine direction based on thresholds
            if prob_buy >= self.config.BUY_THRESHOLD:
                direction = SignalDirection.BUY
                confidence = prob_buy
            elif prob_sell >= self.config.SELL_THRESHOLD:
                direction = SignalDirection.SELL
                confidence = prob_sell
            else:
                direction = SignalDirection.HOLD
                confidence = prob_hold

            # Extract feature values for metadata
            feature_values = X.iloc[0].to_dict()

            return RandomForestPredictionResult(
                probability_buy=float(prob_buy),
                probability_sell=float(prob_sell),
                probability_hold=float(prob_hold),
                predicted_direction=direction,
                confidence=float(confidence),
                tree_agreement=tree_agreement,
                features=feature_values,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error during model prediction: {e}")
            return None

    # ========================================================================
    # Model Persistence
    # ========================================================================

    def _save_model(self) -> None:
        """Save model to disk."""
        if self.model is None:
            logger.warning("No model to save")
            return

        try:
            import pickle

            # Save Random Forest model
            with open(self.model_file, "wb") as f:
                pickle.dump(self.model, f)

            # Save metadata
            metadata = {
                "symbol": self.symbol,
                "model_version": self.model_version,
                "training_samples": self.training_samples,
                "feature_columns": self.config.FEATURE_COLUMNS,
                "feature_importance": self.feature_importance,
                "metrics": self.model_metrics,
                "config": {
                    "n_estimators": self.config.N_ESTIMATORS,
                    "max_depth": self.config.MAX_DEPTH,
                    "min_samples_split": self.config.MIN_SAMPLES_SPLIT,
                    "min_samples_leaf": self.config.MIN_SAMPLES_LEAF,
                    "max_features": self.config.MAX_FEATURES,
                    "buy_threshold": self.config.BUY_THRESHOLD,
                    "sell_threshold": self.config.SELL_THRESHOLD
                },
                "trained_at": datetime.now().isoformat()
            }

            metadata_file = self.model_file.with_suffix(".metadata.json")
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Model saved to {self.model_file}")

        except Exception as e:
            logger.error(f"Error saving model: {e}", exc_info=True)

    def _load_model(self) -> bool:
        """
        Load model from disk.

        Returns:
            True if model loaded successfully, False otherwise
        """
        if not self.model_file.exists():
            logger.debug(f"No model file found at {self.model_file}")
            return False

        try:
            import pickle

            # Load Random Forest model
            with open(self.model_file, "rb") as f:
                self.model = pickle.load(f)

            # Load metadata
            metadata_file = self.model_file.with_suffix(".metadata.json")
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                self.model_version = metadata.get("model_version", "")
                self.training_samples = metadata.get("training_samples", 0)
                self.config.FEATURE_COLUMNS = metadata.get("feature_columns", [])
                self.feature_importance = metadata.get("feature_importance", {})
                self.model_metrics = metadata.get("metrics", {})

                logger.info(f"Model metadata loaded: version={self.model_version}")

            # Set trained flag after successful load
            self._is_trained = True

            logger.info(f"Model loaded from {self.model_file}")
            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            return False

    # ========================================================================
    # Feature Importance
    # ========================================================================

    def get_feature_importance(
        self,
        top_n: int = 20
    ) -> Dict[str, float]:
        """
        Get feature importance scores.

        Args:
            top_n: Number of top features to return

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.feature_importance:
            logger.warning("No feature importance data available")
            return {}

        # Return top N features
        return dict(list(self.feature_importance.items())[:top_n])

    def print_feature_importance(self, top_n: int = 20) -> None:
        """
        Print feature importance in a readable format.

        Args:
            top_n: Number of top features to print
        """
        importance = self.get_feature_importance(top_n)

        if not importance:
            print("No feature importance data available")
            return

        print(f"\nTop {len(importance)} Features for {self.symbol}:")
        print("-" * 60)
        for i, (feature, score) in enumerate(importance.items(), 1):
            print(f"{i:2d}. {feature:30s} : {score:.4f}")

    # ========================================================================
    # Model Info
    # ========================================================================

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the trained model.

        Returns:
            Dictionary with model information
        """
        return {
            "symbol": self.symbol,
            "model_version": self.model_version,
            "is_trained": self._is_trained,
            "is_initialized": self._is_initialized,
            "training_samples": self.training_samples,
            "feature_count": len(self.config.FEATURE_COLUMNS),
            "metrics": self.model_metrics,
            "config": {
                "n_estimators": self.config.N_ESTIMATORS,
                "max_depth": self.config.MAX_DEPTH,
                "min_samples_split": self.config.MIN_SAMPLES_SPLIT,
                "min_samples_leaf": self.config.MIN_SAMPLES_LEAF,
                "max_features": self.config.MAX_FEATURES,
                "buy_threshold": self.config.BUY_THRESHOLD,
                "sell_threshold": self.config.SELL_THRESHOLD
            },
            "model_file": str(self.model_file),
            "top_features": dict(list(self.feature_importance.items())[:5])
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_random_forest_signal_source(
    symbol: str,
    config: Optional[RandomForestConfig] = None
) -> RandomForestSignalSource:
    """
    Factory function to create a Random Forest signal source.

    Args:
        symbol: Trading symbol
        config: Optional Random Forest configuration

    Returns:
        RandomForestSignalSource instance
    """
    return RandomForestSignalSource(symbol=symbol, config=config)


async def create_and_train_rf_source(
    symbol: str,
    historical_data: pd.DataFrame,
    config: Optional[RandomForestConfig] = None
) -> RandomForestSignalSource:
    """
    Create and train a Random Forest signal source.

    Args:
        symbol: Trading symbol
        historical_data: Historical OHLCV data for training
        config: Optional Random Forest configuration

    Returns:
        Trained RandomForestSignalSource instance
    """
    source = RandomForestSignalSource(symbol=symbol, config=config)
    await source.train(historical_data)
    return source


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "RandomForestConfig",
    "RandomForestPredictionResult",
    "RandomForestSignalSource",
    "create_random_forest_signal_source",
    "create_and_train_rf_source"
]
