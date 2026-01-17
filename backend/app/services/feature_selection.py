"""
Feature Selection and Importance Analysis Service.

This module provides comprehensive feature selection capabilities for ML models,
including:
- Feature importance calculation using mutual information
- Feature importance using random forest baseline
- Correlation analysis to remove highly correlated features
- Feature stability analysis (importance over time)
- Recursive feature elimination
- Feature selection based on importance threshold
- Feature importance reports and visualizations
- Selected feature set configuration storage
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
from loguru import logger

try:
    from sklearn.feature_selection import (
        mutual_info_regression,
        mutual_info_classif,
        RFE,
        SelectKBest,
        f_regression,
        f_classif
    )
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import mean_squared_error, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not installed. Some features will be limited.")
    SKLEARN_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("matplotlib not installed. Visualization features will be limited.")
    MATPLOTLIB_AVAILABLE = False


@dataclass
class FeatureImportanceConfig:
    """Configuration for feature importance analysis."""

    # Number of features to select
    n_features: int = 30

    # Importance threshold (0-1)
    importance_threshold: float = 0.01

    # Correlation threshold for removing features
    correlation_threshold: float = 0.95

    # Random forest parameters
    rf_n_estimators: int = 100
    rf_max_depth: Optional[int] = None
    rf_min_samples_split: int = 2
    rf_random_state: int = 42

    # Mutual information parameters
    mi_n_neighbors: int = 3
    mi_random_state: int = 42

    # RFE parameters
    rfe_step: float = 0.1
    rfe_cv: int = 5

    # Stability analysis parameters
    stability_n_splits: int = 5
    stability_test_size: float = 0.2

    # Storage paths
    feature_set_path: str = "backend/data/feature_sets"
    reports_path: str = "backend/data/feature_reports"


@dataclass
class FeatureImportanceResult:
    """Result of feature importance analysis."""

    feature_name: str
    importance_score: float
    rank: int
    method: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class FeatureSelectionResult:
    """Result of feature selection process."""

    selected_features: List[str]
    removed_features: List[str]
    n_selected: int
    n_removed: int
    selection_method: str
    timestamp: datetime
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "selected_features": self.selected_features,
            "removed_features": self.removed_features,
            "n_selected": self.n_selected,
            "n_removed": self.n_removed,
            "selection_method": self.selection_method,
            "timestamp": self.timestamp.isoformat(),
            "config": self.config
        }


@dataclass
class FeatureStabilityResult:
    """Result of feature stability analysis."""

    feature_name: str
    mean_importance: float
    std_importance: float
    stability_score: float  # Lower is more stable
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_name": self.feature_name,
            "mean_importance": self.mean_importance,
            "std_importance": self.std_importance,
            "stability_score": self.stability_score,
            "rank": self.rank
        }


class FeatureSelection:
    """
    Comprehensive feature selection and importance analysis.

    This class provides methods to:
    - Calculate feature importance using mutual information
    - Calculate feature importance using random forest
    - Analyze and remove highly correlated features
    - Analyze feature stability over time
    - Perform recursive feature elimination
    - Select features based on importance threshold
    - Generate feature importance reports and visualizations
    - Store selected feature set configurations

    Usage:
        fs = FeatureSelection()
        result = fs.select_features(X, y, method="combined")
    """

    def __init__(self, config: Optional[FeatureImportanceConfig] = None):
        """
        Initialize FeatureSelection service.

        Args:
            config: Feature importance configuration (uses defaults if not provided)
        """
        self.config = config or FeatureImportanceConfig()

        # Create directories for storing results
        Path(self.config.feature_set_path).mkdir(parents=True, exist_ok=True)
        Path(self.config.reports_path).mkdir(parents=True, exist_ok=True)

        # Feature importance cache
        self._importance_cache: Dict[str, List[FeatureImportanceResult]] = {}

        logger.info("FeatureSelection service initialized")

    # ========================================================================
    # Feature Importance Methods
    # ========================================================================

    def calculate_mutual_information(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        classification: bool = False
    ) -> List[FeatureImportanceResult]:
        """
        Calculate feature importance using mutual information.

        Mutual information measures the dependency between variables.
        Higher values indicate more informative features.

        Args:
            X: Feature DataFrame
            y: Target Series
            classification: Whether this is a classification task

        Returns:
            List of FeatureImportanceResult sorted by importance (descending)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for mutual information calculation")

        logger.info(f"Calculating mutual information for {len(X.columns)} features")

        # Handle missing values - drop features that are all NaN
        X_clean = X.dropna(axis=1, how='all').fillna(X.mean())
        y_clean = y.fillna(y.mean() if not classification else y.mode()[0] if len(y.mode()) > 0 else 0)

        # Get the list of valid features (not all NaN)
        valid_features = X_clean.columns.tolist()

        # Calculate mutual information
        mi_func = mutual_info_classif if classification else mutual_info_regression
        mi_scores = mi_func(
            X_clean,
            y_clean,
            n_neighbors=self.config.mi_n_neighbors,
            random_state=self.config.mi_random_state
        )

        # Create results (only for features that weren't dropped)
        results = []
        for idx, feature in enumerate(valid_features):
            result = FeatureImportanceResult(
                feature_name=feature,
                importance_score=float(mi_scores[idx]),
                rank=0,  # Will be set after sorting
                method="mutual_information"
            )
            results.append(result)

        # Sort by importance and set ranks
        results.sort(key=lambda x: x.importance_score, reverse=True)
        for idx, result in enumerate(results, 1):
            result.rank = idx

        # Cache results
        self._importance_cache["mutual_information"] = results

        logger.info(f"Mutual information calculation complete. Top feature: {results[0].feature_name}")

        return results

    def calculate_random_forest_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        classification: bool = False
    ) -> List[FeatureImportanceResult]:
        """
        Calculate feature importance using random forest.

        Random forest importance measures how much each feature contributes
        to decreasing impurity across all trees in the forest.

        Args:
            X: Feature DataFrame
            y: Target Series
            classification: Whether this is a classification task

        Returns:
            List of FeatureImportanceResult sorted by importance (descending)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for random forest importance calculation")

        logger.info(f"Calculating random forest importance for {len(X.columns)} features")

        # Handle missing values
        X_clean = X.fillna(X.mean())
        y_clean = y.fillna(y.mean() if not classification else y.mode()[0])

        # Create and fit random forest
        rf_class = RandomForestClassifier if classification else RandomForestRegressor
        rf = rf_class(
            n_estimators=self.config.rf_n_estimators,
            max_depth=self.config.rf_max_depth,
            min_samples_split=self.config.rf_min_samples_split,
            random_state=self.config.rf_random_state,
            n_jobs=-1
        )

        rf.fit(X_clean, y_clean)

        # Get feature importances
        importances = rf.feature_importances_

        # Create results
        results = []
        for idx, feature in enumerate(X.columns):
            result = FeatureImportanceResult(
                feature_name=feature,
                importance_score=float(importances[idx]),
                rank=0,
                method="random_forest"
            )
            results.append(result)

        # Sort by importance and set ranks
        results.sort(key=lambda x: x.importance_score, reverse=True)
        for idx, result in enumerate(results, 1):
            result.rank = idx

        # Cache results
        self._importance_cache["random_forest"] = results

        logger.info(f"Random forest importance calculation complete. Top feature: {results[0].feature_name}")

        return results

    def calculate_combined_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        classification: bool = False,
        weights: Optional[Dict[str, float]] = None
    ) -> List[FeatureImportanceResult]:
        """
        Calculate combined feature importance from multiple methods.

        Combines mutual information and random forest importance using
        weighted average to get a more robust importance ranking.

        Args:
            X: Feature DataFrame
            y: Target Series
            classification: Whether this is a classification task
            weights: Weights for each method (default: equal weights)

        Returns:
            List of FeatureImportanceResult sorted by combined importance (descending)
        """
        if weights is None:
            weights = {"mutual_information": 0.5, "random_forest": 0.5}

        logger.info("Calculating combined feature importance")

        # Calculate importance using each method
        mi_results = self.calculate_mutual_information(X, y, classification)
        rf_results = self.calculate_random_forest_importance(X, y, classification)

        # Normalize importance scores to 0-1 range
        def normalize_scores(results: List[FeatureImportanceResult]) -> Dict[str, float]:
            max_score = max(r.importance_score for r in results)
            return {r.feature_name: r.importance_score / max_score for r in results}

        mi_normalized = normalize_scores(mi_results)
        rf_normalized = normalize_scores(rf_results)

        # Calculate combined scores
        combined_scores = {}
        for feature in X.columns:
            score = (
                weights.get("mutual_information", 0.5) * mi_normalized.get(feature, 0) +
                weights.get("random_forest", 0.5) * rf_normalized.get(feature, 0)
            )
            combined_scores[feature] = score

        # Create results
        results = []
        for feature, score in combined_scores.items():
            result = FeatureImportanceResult(
                feature_name=feature,
                importance_score=float(score),
                rank=0,
                method="combined"
            )
            results.append(result)

        # Sort by importance and set ranks
        results.sort(key=lambda x: x.importance_score, reverse=True)
        for idx, result in enumerate(results, 1):
            result.rank = idx

        # Cache results
        self._importance_cache["combined"] = results

        logger.info(f"Combined importance calculation complete. Top feature: {results[0].feature_name}")

        return results

    # ========================================================================
    # Correlation Analysis
    # ========================================================================

    def analyze_correlation(
        self,
        X: pd.DataFrame,
        threshold: Optional[float] = None
    ) -> Tuple[List[Tuple[str, str, float]], List[str]]:
        """
        Analyze feature correlations and identify highly correlated pairs.

        Args:
            X: Feature DataFrame
            threshold: Correlation threshold (default: from config)

        Returns:
            Tuple of (correlated_pairs, features_to_remove)
        """
        if threshold is None:
            threshold = self.config.correlation_threshold

        logger.info(f"Analyzing correlations with threshold {threshold}")

        # Calculate correlation matrix
        corr_matrix = X.corr().abs()

        # Find highly correlated pairs
        correlated_pairs = []
        features_to_remove = set()
        seen_features = set()

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                feature1 = corr_matrix.columns[i]
                feature2 = corr_matrix.columns[j]
                correlation = corr_matrix.iloc[i, j]

                if correlation >= threshold:
                    correlated_pairs.append((feature1, feature2, correlation))

                    # Mark one feature for removal (keep the one that appears earlier)
                    if feature1 not in seen_features and feature2 not in seen_features:
                        features_to_remove.add(feature2)
                        seen_features.add(feature1)
                        seen_features.add(feature2)

        logger.info(
            f"Found {len(correlated_pairs)} highly correlated pairs, "
            f"suggesting removal of {len(features_to_remove)} features"
        )

        return correlated_pairs, sorted(list(features_to_remove))

    def remove_correlated_features(
        self,
        X: pd.DataFrame,
        importance_results: Optional[List[FeatureImportanceResult]] = None,
        threshold: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Remove highly correlated features, keeping the most important ones.

        Args:
            X: Feature DataFrame
            importance_results: Feature importance results (used to decide which to keep)
            threshold: Correlation threshold (default: from config)

        Returns:
            DataFrame with correlated features removed
        """
        correlated_pairs, features_to_remove = self.analyze_correlation(X, threshold)

        if importance_results:
            # Create importance mapping
            importance_map = {r.feature_name: (r.rank, r.importance_score) for r in importance_results}

            # For each correlated pair, keep the more important feature
            final_features_to_remove = []
            for feature in features_to_remove:
                # Find which feature it's correlated with
                for feat1, feat2, _ in correlated_pairs:
                    if feature == feat2:
                        # Check if feature1 is more important
                        if (feat1 in importance_map and feat2 in importance_map and
                            importance_map[feat1][0] < importance_map[feat2][0]):
                            final_features_to_remove.append(feature)
                            break
                        elif feat1 not in importance_map and feat2 in importance_map:
                            # Keep feature2 if feature1 not in importance results
                            break
                        elif feat1 in importance_map and feat2 not in importance_map:
                            # Remove feature2 if feature1 is in importance results
                            final_features_to_remove.append(feature)
                            break
            features_to_remove = final_features_to_remove

        # Remove correlated features
        X_reduced = X.drop(columns=features_to_remove, errors='ignore')

        logger.info(
            f"Removed {len(features_to_remove)} correlated features. "
            f"Remaining: {len(X_reduced.columns)} features"
        )

        return X_reduced

    # ========================================================================
    # Feature Stability Analysis
    # ========================================================================

    def analyze_feature_stability(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        classification: bool = False,
        n_splits: Optional[int] = None
    ) -> List[FeatureStabilityResult]:
        """
        Analyze feature stability by measuring importance variance across time splits.

        Stable features maintain consistent importance across different time periods,
        indicating robust predictive power rather than overfitting to recent patterns.

        Args:
            X: Feature DataFrame
            y: Target Series
            classification: Whether this is a classification task
            n_splits: Number of time splits to analyze (default: from config)

        Returns:
            List of FeatureStabilityResult sorted by stability score (ascending)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for feature stability analysis")

        if n_splits is None:
            n_splits = self.config.stability_n_splits

        logger.info(f"Analyzing feature stability with {n_splits} splits")

        n_samples = len(X)
        split_size = n_samples // (n_splits + 1)

        # Store importance scores for each split
        importance_history: Dict[str, List[float]] = {}

        for i in range(n_splits):
            # Use rolling windows for time-based splits
            start_idx = i * split_size
            end_idx = start_idx + int(n_samples * (1 - self.config.stability_test_size))

            if end_idx > n_samples:
                end_idx = n_samples

            X_split = X.iloc[start_idx:end_idx]
            y_split = y.iloc[start_idx:end_idx]

            if len(X_split) < 10:  # Skip if too small
                continue

            # Calculate random forest importance for this split
            try:
                rf = (RandomForestClassifier if classification else RandomForestRegressor)(
                    n_estimators=50,  # Use fewer trees for speed
                    max_depth=10,
                    random_state=self.config.rf_random_state + i,
                    n_jobs=-1
                )

                X_clean = X_split.fillna(X_split.mean())
                y_clean = y_split.fillna(y_split.mean() if not classification else y_split.mode()[0])

                rf.fit(X_clean, y_clean)

                for idx, feature in enumerate(X.columns):
                    if feature not in importance_history:
                        importance_history[feature] = []
                    importance_history[feature].append(float(rf.feature_importances_[idx]))

            except Exception as e:
                logger.warning(f"Error in split {i}: {e}")
                continue

        # Calculate stability metrics
        results = []
        for feature, scores in importance_history.items():
            if len(scores) < 2:
                continue

            mean_importance = np.mean(scores)
            std_importance = np.std(scores)

            # Stability score: coefficient of variation (lower = more stable)
            stability_score = std_importance / (mean_importance + 1e-10)

            result = FeatureStabilityResult(
                feature_name=feature,
                mean_importance=float(mean_importance),
                std_importance=float(std_importance),
                stability_score=float(stability_score),
                rank=0
            )
            results.append(result)

        # Sort by stability score (lower is better)
        results.sort(key=lambda x: x.stability_score)
        for idx, result in enumerate(results, 1):
            result.rank = idx

        logger.info(f"Feature stability analysis complete. Most stable: {results[0].feature_name}")

        return results

    # ========================================================================
    # Feature Selection Methods
    # ========================================================================

    def select_by_threshold(
        self,
        importance_results: List[FeatureImportanceResult],
        threshold: Optional[float] = None
    ) -> List[str]:
        """
        Select features based on importance threshold.

        Args:
            importance_results: Feature importance results
            threshold: Minimum importance score (default: from config)

        Returns:
            List of selected feature names
        """
        if threshold is None:
            threshold = self.config.importance_threshold

        selected = [
            r.feature_name for r in importance_results
            if r.importance_score >= threshold
        ]

        logger.info(f"Selected {len(selected)} features with importance >= {threshold}")

        return selected

    def select_top_k(
        self,
        importance_results: List[FeatureImportanceResult],
        k: Optional[int] = None
    ) -> List[str]:
        """
        Select top k features by importance.

        Args:
            importance_results: Feature importance results
            k: Number of features to select (default: from config)

        Returns:
            List of selected feature names
        """
        if k is None:
            k = self.config.n_features

        selected = [r.feature_name for r in importance_results[:k]]

        logger.info(f"Selected top {len(selected)} features")

        return selected

    def recursive_feature_elimination(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_features: Optional[int] = None,
        classification: bool = False
    ) -> List[str]:
        """
        Perform recursive feature elimination (RFE).

        RFE recursively removes less important features and builds a model
        on the remaining features to identify the optimal subset.

        Args:
            X: Feature DataFrame
            y: Target Series
            n_features: Number of features to select (default: from config)
            classification: Whether this is a classification task

        Returns:
            List of selected feature names
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for RFE")

        if n_features is None:
            n_features = self.config.n_features

        logger.info(f"Performing RFE to select {n_features} features")

        # Handle missing values
        X_clean = X.fillna(X.mean())
        y_clean = y.fillna(y.mean() if not classification else y.mode()[0])

        # Create base estimator
        rf_class = RandomForestClassifier if classification else RandomForestRegressor
        estimator = rf_class(
            n_estimators=50,
            random_state=self.config.rf_random_state,
            n_jobs=-1
        )

        # Perform RFE
        rfe = RFE(
            estimator=estimator,
            n_features_to_select=n_features,
            step=self.config.rfe_step
        )

        rfe.fit(X_clean, y_clean)

        # Get selected features
        selected = [feature for feature, selected in zip(X.columns, rfe.support_) if selected]

        logger.info(f"RFE complete. Selected {len(selected)} features")

        return selected

    def select_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        method: str = "combined",
        classification: bool = False,
        remove_correlated: bool = True
    ) -> FeatureSelectionResult:
        """
        Select features using the specified method.

        This is the main entry point for feature selection, combining
        importance calculation, correlation analysis, and feature elimination.

        Args:
            X: Feature DataFrame
            y: Target Series
            method: Selection method ("mutual_information", "random_forest", "combined", "rfe")
            classification: Whether this is a classification task
            remove_correlated: Whether to remove highly correlated features

        Returns:
            FeatureSelectionResult with selected features and metadata
        """
        logger.info(f"Starting feature selection with method: {method}")

        initial_features = list(X.columns)

        # Calculate feature importance
        if method == "mutual_information":
            importance_results = self.calculate_mutual_information(X, y, classification)
            selected = self.select_top_k(importance_results)
        elif method == "random_forest":
            importance_results = self.calculate_random_forest_importance(X, y, classification)
            selected = self.select_top_k(importance_results)
        elif method == "combined":
            importance_results = self.calculate_combined_importance(X, y, classification)
            selected = self.select_top_k(importance_results)
        elif method == "rfe":
            selected = self.recursive_feature_elimination(X, y, classification=classification)
            importance_results = []
        else:
            raise ValueError(f"Unknown selection method: {method}")

        # Remove correlated features if requested
        if remove_correlated and method != "rfe":
            X_selected = X[selected]
            importance_to_use = importance_results if importance_results else None
            X_reduced = self.remove_correlated_features(X_selected, importance_to_use)
            selected = list(X_reduced.columns)

        # Determine removed features
        removed = [f for f in initial_features if f not in selected]

        result = FeatureSelectionResult(
            selected_features=selected,
            removed_features=removed,
            n_selected=len(selected),
            n_removed=len(removed),
            selection_method=method,
            timestamp=datetime.now(),
            config={
                "n_features_target": self.config.n_features,
                "importance_threshold": self.config.importance_threshold,
                "correlation_threshold": self.config.correlation_threshold,
                "remove_correlated": remove_correlated
            }
        )

        logger.info(
            f"Feature selection complete: {len(selected)} selected, {len(removed)} removed"
        )

        return result

    # ========================================================================
    # Reporting and Visualization
    # ========================================================================

    def generate_importance_report(
        self,
        importance_results: List[FeatureImportanceResult],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a feature importance report.

        Args:
            importance_results: Feature importance results
            output_path: Path to save the report (optional)

        Returns:
            Dictionary containing the report data
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "n_features": len(importance_results),
            "method": importance_results[0].method if importance_results else "unknown",
            "top_features": [
                {
                    "rank": r.rank,
                    "feature": r.feature_name,
                    "importance": r.importance_score
                }
                for r in importance_results[:20]
            ],
            "summary": {
                "highest_importance": importance_results[0].importance_score if importance_results else 0,
                "lowest_importance": importance_results[-1].importance_score if importance_results else 0,
                "mean_importance": np.mean([r.importance_score for r in importance_results]) if importance_results else 0,
                "std_importance": np.std([r.importance_score for r in importance_results]) if importance_results else 0
            }
        }

        if output_path:
            output_file = Path(output_path) / f"importance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Importance report saved to {output_file}")

        return report

    def plot_importance(
        self,
        importance_results: List[FeatureImportanceResult],
        top_n: int = 20,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create a feature importance visualization.

        Args:
            importance_results: Feature importance results
            top_n: Number of top features to display
            output_path: Path to save the plot

        Returns:
            Path to the saved plot
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available, skipping plot generation")
            return ""

        # Get top features
        top_features = importance_results[:top_n]

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        features = [r.feature_name for r in top_features]
        scores = [r.importance_score for r in top_features]

        y_pos = np.arange(len(features))
        ax.barh(y_pos, scores, align='center', color='#3b82f6')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.invert_yaxis()
        ax.set_xlabel('Importance Score')
        ax.set_title(f'Top {top_n} Feature Importance ({top_features[0].method if top_features else "Unknown"})')
        ax.set_xlim(0, max(scores) * 1.1)

        plt.tight_layout()

        # Save plot
        if output_path is None:
            output_path = self.config.reports_path

        output_file = Path(output_path) / f"importance_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"Importance plot saved to {output_file}")

        return str(output_file)

    def plot_correlation_matrix(
        self,
        X: pd.DataFrame,
        top_n: int = 30,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create a correlation matrix heatmap.

        Args:
            X: Feature DataFrame
            top_n: Number of top features to display (based on variance)
            output_path: Path to save the plot

        Returns:
            Path to the saved plot
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available, skipping plot generation")
            return ""

        # Select top features by variance
        variances = X.var().sort_values(ascending=False)
        top_features = variances.head(top_n).index.tolist()
        X_top = X[top_features]

        # Calculate correlation
        corr = X_top.corr()

        # Create plot
        fig, ax = plt.subplots(figsize=(14, 12))

        im = ax.imshow(corr, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

        # Set ticks
        ax.set_xticks(np.arange(len(top_features)))
        ax.set_yticks(np.arange(len(top_features)))
        ax.set_xticklabels(top_features, rotation=90, fontsize=8)
        ax.set_yticklabels(top_features, fontsize=8)

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Correlation', rotation=270, labelpad=20)

        # Add correlation values
        for i in range(len(top_features)):
            for j in range(len(top_features)):
                text = ax.text(j, i, f'{corr.iloc[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=6)

        ax.set_title(f'Feature Correlation Matrix (Top {top_n} by Variance)')
        plt.tight_layout()

        # Save plot
        if output_path is None:
            output_path = self.config.reports_path

        output_file = Path(output_path) / f"correlation_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"Correlation matrix saved to {output_file}")

        return str(output_file)

    def plot_stability_analysis(
        self,
        stability_results: List[FeatureStabilityResult],
        top_n: int = 20,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create a feature stability visualization.

        Args:
            stability_results: Feature stability results
            top_n: Number of top features to display
            output_path: Path to save the plot

        Returns:
            Path to the saved plot
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available, skipping plot generation")
            return ""

        # Get most stable features (lowest stability score)
        stable_features = stability_results[:top_n]

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        features = [r.feature_name for r in stable_features]
        mean_scores = [r.mean_importance for r in stable_features]
        errors = [r.std_importance for r in stable_features]

        y_pos = np.arange(len(features))
        ax.barh(y_pos, mean_scores, xerr=errors, align='center',
               color='#10b981', alpha=0.8, capsize=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.invert_yaxis()
        ax.set_xlabel('Mean Importance Score')
        ax.set_title(f'Top {top_n} Most Stable Features (Error Bars = Std Dev)')
        ax.set_xlim(0, max([m + e for m, e in zip(mean_scores, errors)]) * 1.1)

        plt.tight_layout()

        # Save plot
        if output_path is None:
            output_path = self.config.reports_path

        output_file = Path(output_path) / f"stability_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"Stability analysis plot saved to {output_file}")

        return str(output_file)

    # ========================================================================
    # Configuration Storage
    # ========================================================================

    def save_feature_set(
        self,
        selection_result: FeatureSelectionResult,
        name: str
    ) -> str:
        """
        Save a selected feature set configuration to disk.

        Args:
            selection_result: Feature selection result
            name: Name for this feature set

        Returns:
            Path to the saved configuration
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"feature_set_{name}_{timestamp}.json"
        output_path = Path(self.config.feature_set_path) / filename

        config_data = {
            "name": name,
            "timestamp": selection_result.timestamp.isoformat(),
            "features": selection_result.selected_features,
            "n_features": selection_result.n_selected,
            "method": selection_result.selection_method,
            "config": selection_result.config
        }

        with open(output_path, 'w') as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Feature set saved to {output_path}")

        return str(output_path)

    def load_feature_set(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a feature set configuration from disk.

        Args:
            name: Name of the feature set to load

        Returns:
            Dictionary containing the feature set configuration, or None if not found
        """
        # Find the most recent file matching the name
        files = list(Path(self.config.feature_set_path).glob(f"feature_set_{name}_*.json"))

        if not files:
            logger.warning(f"No feature set found with name: {name}")
            return None

        # Load the most recent file
        latest_file = max(files, key=lambda f: f.stat().st_mtime)

        with open(latest_file, 'r') as f:
            config_data = json.load(f)

        logger.info(f"Loaded feature set from {latest_file}")

        return config_data


# ============================================================================
# Convenience Functions
# ============================================================================

def create_feature_selector(
    config: Optional[FeatureImportanceConfig] = None
) -> FeatureSelection:
    """
    Factory function to create a FeatureSelection instance.

    Args:
        config: Optional feature selection configuration

    Returns:
        FeatureSelection instance
    """
    return FeatureSelection(config=config)


def select_features_auto(
    X: pd.DataFrame,
    y: pd.Series,
    n_features: int = 30,
    classification: bool = False
) -> List[str]:
    """
    Automatically select features using combined method.

    Args:
        X: Feature DataFrame
        y: Target Series
        n_features: Number of features to select
        classification: Whether this is a classification task

    Returns:
        List of selected feature names
    """
    config = FeatureImportanceConfig(n_features=n_features)
    fs = FeatureSelection(config)
    result = fs.select_features(X, y, method="combined", classification=classification)
    return result.selected_features
