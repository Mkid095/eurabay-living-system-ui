"""
Test suite for Feature Selection Service.

Tests all feature selection functionality including:
- Feature importance calculation using mutual information
- Feature importance using random forest
- Correlation analysis and removal
- Feature stability analysis
- Recursive feature elimination
- Feature selection based on threshold and top-k
- Feature importance reports and visualizations
- Configuration storage
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json
import tempfile
import shutil

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.feature_selection import (
    FeatureSelection,
    FeatureImportanceConfig,
    FeatureImportanceResult,
    FeatureSelectionResult,
    FeatureStabilityResult,
    create_feature_selector,
    select_features_auto,
    SKLEARN_AVAILABLE
)


# ============================================================================
# Skip tests if scikit-learn not available
# ============================================================================

pytestmark = pytest.mark.skipif(
    not SKLEARN_AVAILABLE,
    reason="scikit-learn not installed"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_feature_data():
    """Generate sample feature data for testing."""
    np.random.seed(42)

    n_samples = 200
    n_features = 30

    # Generate correlated features
    base_data = np.random.randn(n_samples, 10)

    # Create feature names
    feature_names = [f"feature_{i}" for i in range(n_features)]

    # Build feature matrix with some correlations
    data = {}
    for i in range(n_features):
        if i < 10:
            # Base features
            data[feature_names[i]] = base_data[:, i]
        elif i < 20:
            # Correlated with base features (add noise)
            base_idx = i - 10
            data[feature_names[i]] = base_data[:, base_idx] + np.random.randn(n_samples) * 0.1
        else:
            # Independent features
            data[feature_names[i]] = np.random.randn(n_samples)

    # Create target with relationship to some features
    target = (
        0.5 * data["feature_0"] +
        0.3 * data["feature_1"] +
        0.2 * data["feature_2"] +
        0.1 * np.random.randn(n_samples)
    )

    X = pd.DataFrame(data)
    y = pd.Series(target, name="target")

    return X, y


@pytest.fixture
def classification_data():
    """Generate sample classification data for testing."""
    np.random.seed(42)

    n_samples = 200
    n_features = 20

    # Generate features
    feature_names = [f"feature_{i}" for i in range(n_features)]
    data = {name: np.random.randn(n_samples) for name in feature_names}

    # Create binary target based on first few features
    logit = (
        0.5 * data["feature_0"] +
        0.3 * data["feature_1"] +
        0.2 * data["feature_2"]
    )
    prob = 1 / (1 + np.exp(-logit))
    target = (np.random.rand(n_samples) < prob).astype(int)

    X = pd.DataFrame(data)
    y = pd.Series(target, name="target")

    return X, y


@pytest.fixture
def feature_selector():
    """Create a FeatureSelection instance for testing."""
    return FeatureSelection()


@pytest.fixture
def custom_config():
    """Create a custom FeatureImportanceConfig for testing."""
    return FeatureImportanceConfig(
        n_features=15,
        importance_threshold=0.02,
        correlation_threshold=0.9,
        rf_n_estimators=50,
        mi_n_neighbors=3
    )


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


# ============================================================================
# Initialization Tests
# ============================================================================

class TestFeatureSelectionInitialization:
    """Test FeatureSelection initialization."""

    def test_default_initialization(self):
        """Test initialization with default configuration."""
        fs = FeatureSelection()
        assert fs.config is not None
        assert fs.config.n_features == 30
        assert fs.config.importance_threshold == 0.01
        assert fs.config.correlation_threshold == 0.95

    def test_custom_config_initialization(self, custom_config):
        """Test initialization with custom configuration."""
        fs = FeatureSelection(config=custom_config)
        assert fs.config.n_features == 15
        assert fs.config.importance_threshold == 0.02
        assert fs.config.correlation_threshold == 0.9

    def test_directory_creation(self, temp_dir):
        """Test that storage directories are created."""
        config = FeatureImportanceConfig(
            feature_set_path=f"{temp_dir}/feature_sets",
            reports_path=f"{temp_dir}/reports"
        )
        fs = FeatureSelection(config=config)

        assert Path(config.feature_set_path).exists()
        assert Path(config.reports_path).exists()


# ============================================================================
# Mutual Information Tests
# ============================================================================

class TestMutualInformation:
    """Test mutual information feature importance calculation."""

    def test_calculate_mutual_information_regression(self, feature_selector, sample_feature_data):
        """Test mutual information calculation for regression."""
        X, y = sample_feature_data

        results = feature_selector.calculate_mutual_information(X, y, classification=False)

        assert len(results) == len(X.columns)
        assert all(isinstance(r, FeatureImportanceResult) for r in results)
        assert results[0].rank == 1
        assert results[0].method == "mutual_information"
        assert results[0].importance_score >= 0

        # Check ranking is correct
        for i in range(1, len(results)):
            assert results[i].rank == i + 1
            assert results[i].importance_score <= results[i-1].importance_score

    def test_calculate_mutual_information_classification(self, feature_selector, classification_data):
        """Test mutual information calculation for classification."""
        X, y = classification_data

        results = feature_selector.calculate_mutual_information(X, y, classification=True)

        assert len(results) == len(X.columns)
        assert all(r.importance_score >= 0 for r in results)
        assert results[0].method == "mutual_information"

    def test_mutual_information_cache(self, feature_selector, sample_feature_data):
        """Test that results are cached."""
        X, y = sample_feature_data

        results1 = feature_selector.calculate_mutual_information(X, y)
        results2 = feature_selector.calculate_mutual_information(X, y)

        assert "mutual_information" in feature_selector._importance_cache
        assert len(results1) == len(results2)

    def test_mutual_information_with_missing_values(self, feature_selector):
        """Test handling of missing values."""
        np.random.seed(42)
        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.random.randn(100),
            "feature_2": np.random.randn(100)
        })
        y = pd.Series(np.random.randn(100))

        # Add missing values
        X.iloc[10:15, 0] = np.nan
        y.iloc[20:25] = np.nan

        results = feature_selector.calculate_mutual_information(X, y)

        assert len(results) == 3
        assert all(not np.isnan(r.importance_score) for r in results)


# ============================================================================
# Random Forest Importance Tests
# ============================================================================

class TestRandomForestImportance:
    """Test random forest feature importance calculation."""

    def test_calculate_rf_importance_regression(self, feature_selector, sample_feature_data):
        """Test random forest importance calculation for regression."""
        X, y = sample_feature_data

        results = feature_selector.calculate_random_forest_importance(X, y, classification=False)

        assert len(results) == len(X.columns)
        assert all(isinstance(r, FeatureImportanceResult) for r in results)
        assert results[0].rank == 1
        assert results[0].method == "random_forest"
        assert all(0 <= r.importance_score <= 1 for r in results)

    def test_calculate_rf_importance_classification(self, feature_selector, classification_data):
        """Test random forest importance calculation for classification."""
        X, y = classification_data

        results = feature_selector.calculate_random_forest_importance(X, y, classification=True)

        assert len(results) == len(X.columns)
        assert all(0 <= r.importance_score <= 1 for r in results)
        assert results[0].method == "random_forest"

    def test_rf_importance_cache(self, feature_selector, sample_feature_data):
        """Test that results are cached."""
        X, y = sample_feature_data

        results1 = feature_selector.calculate_random_forest_importance(X, y)
        results2 = feature_selector.calculate_random_forest_importance(X, y)

        assert "random_forest" in feature_selector._importance_cache
        assert len(results1) == len(results2)

    def test_rf_custom_parameters(self, custom_config, sample_feature_data):
        """Test random forest with custom parameters."""
        fs = FeatureSelection(config=custom_config)
        X, y = sample_feature_data

        results = fs.calculate_random_forest_importance(X, y)

        assert len(results) == len(X.columns)
        assert all(r.importance_score >= 0 for r in results)


# ============================================================================
# Combined Importance Tests
# ============================================================================

class TestCombinedImportance:
    """Test combined feature importance calculation."""

    def test_calculate_combined_importance(self, feature_selector, sample_feature_data):
        """Test combined importance calculation."""
        X, y = sample_feature_data

        results = feature_selector.calculate_combined_importance(X, y, classification=False)

        assert len(results) == len(X.columns)
        assert results[0].method == "combined"
        assert all(r.importance_score >= 0 for r in results)
        assert all(r.importance_score <= 1 for r in results)

    def test_combined_importance_with_weights(self, feature_selector, sample_feature_data):
        """Test combined importance with custom weights."""
        X, y = sample_feature_data

        weights = {"mutual_information": 0.7, "random_forest": 0.3}
        results = feature_selector.calculate_combined_importance(X, y, weights=weights)

        assert len(results) == len(X.columns)
        assert all(r.importance_score >= 0 for r in results)

    def test_combined_importance_cache(self, feature_selector, sample_feature_data):
        """Test that results are cached."""
        X, y = sample_feature_data

        results = feature_selector.calculate_combined_importance(X, y)

        assert "combined" in feature_selector._importance_cache


# ============================================================================
# Correlation Analysis Tests
# ============================================================================

class TestCorrelationAnalysis:
    """Test correlation analysis and feature removal."""

    def test_analyze_correlation(self, feature_selector):
        """Test correlation analysis."""
        np.random.seed(42)

        # Create features with known correlations
        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.random.randn(100),
            "feature_2": np.random.randn(100),
            "feature_3": np.random.randn(100) * 0.99 + 0.01  # Highly correlated with feature_0
        })
        X["feature_3"] = X["feature_0"] * 0.98 + np.random.randn(100) * 0.02

        pairs, to_remove = feature_selector.analyze_correlation(X, threshold=0.95)

        assert len(pairs) > 0
        assert len(to_remove) > 0
        assert all(isinstance(pair, tuple) and len(pair) == 3 for pair in pairs)

    def test_analyze_correlation_custom_threshold(self, feature_selector):
        """Test correlation analysis with custom threshold."""
        np.random.seed(42)

        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.random.randn(100)
        })
        X["feature_1"] = X["feature_0"] * 0.9 + np.random.randn(100) * 0.1

        pairs_low, _ = feature_selector.analyze_correlation(X, threshold=0.8)
        pairs_high, _ = feature_selector.analyze_correlation(X, threshold=0.99)

        assert len(pairs_low) >= len(pairs_high)

    def test_remove_correlated_features(self, feature_selector):
        """Test removal of correlated features."""
        np.random.seed(42)

        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.random.randn(100),
            "feature_2": np.random.randn(100),
            "feature_3": np.random.randn(100),
            "feature_4": np.random.randn(100)
        })

        # Create highly correlated features
        X["feature_3"] = X["feature_0"] * 0.99 + np.random.randn(100) * 0.01
        X["feature_4"] = X["feature_1"] * 0.98 + np.random.randn(100) * 0.02

        X_reduced = feature_selector.remove_correlated_features(X, threshold=0.95)

        assert len(X_reduced.columns) < len(X.columns)
        assert "feature_0" in X_reduced.columns
        assert "feature_1" in X_reduced.columns

    def test_remove_correlated_with_importance(self, feature_selector, sample_feature_data):
        """Test that important features are kept when removing correlated ones."""
        X, y = sample_feature_data

        # Calculate importance
        importance_results = feature_selector.calculate_mutual_information(X, y)

        # Add correlated feature
        X["correlated_with_0"] = X["feature_0"] * 0.99 + np.random.randn(len(X)) * 0.01

        X_reduced = feature_selector.remove_correlated_features(X, importance_results)

        # Feature_0 should be kept (more important), correlated_with_0 should be removed
        assert "feature_0" in X_reduced.columns
        assert len(X_reduced.columns) < len(X.columns)


# ============================================================================
# Feature Stability Tests
# ============================================================================

class TestFeatureStability:
    """Test feature stability analysis."""

    def test_analyze_feature_stability(self, feature_selector, sample_feature_data):
        """Test feature stability analysis."""
        X, y = sample_feature_data

        results = feature_selector.analyze_feature_stability(X, y, n_splits=3)

        assert len(results) > 0
        assert all(isinstance(r, FeatureStabilityResult) for r in results)
        assert all(r.stability_score >= 0 for r in results)
        assert results[0].rank == 1

    def test_stability_score_ordering(self, feature_selector, sample_feature_data):
        """Test that results are ordered by stability score (lower is better)."""
        X, y = sample_feature_data

        results = feature_selector.analyze_feature_stability(X, y, n_splits=3)

        for i in range(1, len(results)):
            assert results[i].stability_score >= results[i-1].stability_score

    def test_stability_with_small_dataset(self, feature_selector):
        """Test stability analysis with small dataset."""
        np.random.seed(42)

        X = pd.DataFrame({
            f"feature_{i}": np.random.randn(50)
            for i in range(10)
        })
        y = pd.Series(np.random.randn(50))

        results = feature_selector.analyze_feature_stability(X, y, n_splits=2)

        assert len(results) > 0


# ============================================================================
# Feature Selection Tests
# ============================================================================

class TestFeatureSelection:
    """Test feature selection methods."""

    def test_select_by_threshold(self, feature_selector, sample_feature_data):
        """Test feature selection by importance threshold."""
        X, y = sample_feature_data

        importance_results = feature_selector.calculate_mutual_information(X, y)
        selected = feature_selector.select_by_threshold(importance_results, threshold=0.05)

        assert len(selected) > 0
        assert len(selected) <= len(importance_results)
        assert all(isinstance(f, str) for f in selected)

    def test_select_by_threshold_default(self, feature_selector, sample_feature_data):
        """Test feature selection with default threshold from config."""
        X, y = sample_feature_data

        importance_results = feature_selector.calculate_mutual_information(X, y)
        selected = feature_selector.select_by_threshold(importance_results)

        assert isinstance(selected, list)

    def test_select_top_k(self, feature_selector, sample_feature_data):
        """Test selecting top k features."""
        X, y = sample_feature_data

        importance_results = feature_selector.calculate_mutual_information(X, y)
        selected = feature_selector.select_top_k(importance_results, k=10)

        assert len(selected) == 10
        assert selected == [r.feature_name for r in importance_results[:10]]

    def test_recursive_feature_elimination(self, feature_selector, sample_feature_data):
        """Test recursive feature elimination."""
        X, y = sample_feature_data

        selected = feature_selector.recursive_feature_elimination(X, y, n_features=15)

        assert len(selected) == 15
        assert all(f in X.columns for f in selected)

    def test_recursive_feature_elimination_classification(self, feature_selector, classification_data):
        """Test RFE for classification."""
        X, y = classification_data

        selected = feature_selector.recursive_feature_elimination(
            X, y, n_features=10, classification=True
        )

        assert len(selected) == 10

    def test_select_features_mutual_information(self, feature_selector, sample_feature_data):
        """Test select_features with mutual_information method."""
        X, y = sample_feature_data

        result = feature_selector.select_features(X, y, method="mutual_information")

        assert isinstance(result, FeatureSelectionResult)
        assert result.n_selected > 0
        assert result.n_selected <= len(X.columns)
        assert result.selection_method == "mutual_information"
        assert all(f in X.columns for f in result.selected_features)

    def test_select_features_random_forest(self, feature_selector, sample_feature_data):
        """Test select_features with random_forest method."""
        X, y = sample_feature_data

        result = feature_selector.select_features(X, y, method="random_forest")

        assert isinstance(result, FeatureSelectionResult)
        assert result.n_selected > 0
        assert result.selection_method == "random_forest"

    def test_select_features_combined(self, feature_selector, sample_feature_data):
        """Test select_features with combined method."""
        X, y = sample_feature_data

        result = feature_selector.select_features(X, y, method="combined")

        assert isinstance(result, FeatureSelectionResult)
        assert result.n_selected > 0
        assert result.selection_method == "combined"

    def test_select_features_rfe(self, feature_selector, sample_feature_data):
        """Test select_features with RFE method."""
        X, y = sample_feature_data

        result = feature_selector.select_features(X, y, method="rfe")

        assert isinstance(result, FeatureSelectionResult)
        assert result.selection_method == "rfe"

    def test_select_features_without_correlation_removal(self, feature_selector, sample_feature_data):
        """Test select_features without removing correlated features."""
        X, y = sample_feature_data

        result = feature_selector.select_features(X, y, method="combined", remove_correlated=False)

        assert isinstance(result, FeatureSelectionResult)
        assert result.config["remove_correlated"] is False

    def test_select_features_invalid_method(self, feature_selector, sample_feature_data):
        """Test that invalid method raises error."""
        X, y = sample_feature_data

        with pytest.raises(ValueError, match="Unknown selection method"):
            feature_selector.select_features(X, y, method="invalid_method")


# ============================================================================
# Reporting and Visualization Tests
# ============================================================================

class TestReporting:
    """Test report generation and visualization."""

    def test_generate_importance_report(self, feature_selector, sample_feature_data):
        """Test importance report generation."""
        X, y = sample_feature_data

        importance_results = feature_selector.calculate_mutual_information(X, y)
        report = feature_selector.generate_importance_report(importance_results)

        assert "timestamp" in report
        assert "n_features" in report
        assert "method" in report
        assert "top_features" in report
        assert "summary" in report
        assert len(report["top_features"]) == min(20, len(importance_results))

    def test_generate_importance_report_with_file(self, feature_selector, sample_feature_data, temp_dir):
        """Test importance report generation with file output."""
        X, y = sample_feature_data

        importance_results = feature_selector.calculate_mutual_information(X, y)
        report = feature_selector.generate_importance_report(importance_results, output_path=temp_dir)

        # Check that file was created
        files = list(Path(temp_dir).glob("importance_report_*.json"))
        assert len(files) > 0

        # Verify file contents
        with open(files[0], 'r') as f:
            saved_report = json.load(f)

        assert saved_report["n_features"] == report["n_features"]

    def test_plot_importance(self, feature_selector, sample_feature_data, temp_dir):
        """Test importance plot generation."""
        X, y = sample_feature_data

        importance_results = feature_selector.calculate_mutual_information(X, y)
        plot_path = feature_selector.plot_importance(importance_results, output_path=temp_dir)

        # Check that file was created
        if plot_path:  # Only check if matplotlib is available
            assert Path(plot_path).exists()
            assert plot_path.endswith(".png")

    def test_plot_correlation_matrix(self, feature_selector, sample_feature_data, temp_dir):
        """Test correlation matrix plot generation."""
        X, _ = sample_feature_data

        plot_path = feature_selector.plot_correlation_matrix(X, output_path=temp_dir)

        # Check that file was created
        if plot_path:  # Only check if matplotlib is available
            assert Path(plot_path).exists()
            assert plot_path.endswith(".png")

    def test_plot_stability_analysis(self, feature_selector, sample_feature_data, temp_dir):
        """Test stability analysis plot generation."""
        X, y = sample_feature_data

        stability_results = feature_selector.analyze_feature_stability(X, y, n_splits=3)
        plot_path = feature_selector.plot_stability_analysis(stability_results, output_path=temp_dir)

        # Check that file was created
        if plot_path:  # Only check if matplotlib is available
            assert Path(plot_path).exists()
            assert plot_path.endswith(".png")


# ============================================================================
# Configuration Storage Tests
# ============================================================================

class TestConfigurationStorage:
    """Test configuration storage and loading."""

    def test_save_feature_set(self, feature_selector, temp_dir):
        """Test saving feature set configuration."""
        config = FeatureImportanceConfig(
            feature_set_path=f"{temp_dir}/feature_sets",
            reports_path=f"{temp_dir}/reports"
        )
        fs = FeatureSelection(config=config)

        selection_result = FeatureSelectionResult(
            selected_features=["feature_0", "feature_1", "feature_2"],
            removed_features=["feature_3", "feature_4"],
            n_selected=3,
            n_removed=2,
            selection_method="combined",
            timestamp=datetime.now(),
            config={}
        )

        saved_path = fs.save_feature_set(selection_result, name="test_set")

        assert Path(saved_path).exists()
        assert "test_set" in saved_path

    def test_load_feature_set(self, feature_selector, temp_dir):
        """Test loading feature set configuration."""
        config = FeatureImportanceConfig(
            feature_set_path=f"{temp_dir}/feature_sets",
            reports_path=f"{temp_dir}/reports"
        )
        fs = FeatureSelection(config=config)

        # First save a feature set
        selection_result = FeatureSelectionResult(
            selected_features=["feature_0", "feature_1", "feature_2"],
            removed_features=["feature_3"],
            n_selected=3,
            n_removed=1,
            selection_method="combined",
            timestamp=datetime.now(),
            config={}
        )

        fs.save_feature_set(selection_result, name="test_load")

        # Now load it
        loaded_config = fs.load_feature_set("test_load")

        assert loaded_config is not None
        assert loaded_config["name"] == "test_load"
        assert loaded_config["n_features"] == 3
        assert loaded_config["features"] == ["feature_0", "feature_1", "feature_2"]

    def test_load_nonexistent_feature_set(self, feature_selector):
        """Test loading non-existent feature set returns None."""
        result = feature_selector.load_feature_set("nonexistent_set")
        assert result is None


# ============================================================================
# Convenience Functions Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_feature_selector(self):
        """Test factory function for creating selector."""
        fs = create_feature_selector()
        assert isinstance(fs, FeatureSelection)

    def test_create_feature_selector_with_config(self, custom_config):
        """Test factory function with custom config."""
        fs = create_feature_selector(config=custom_config)
        assert fs.config.n_features == 15

    def test_select_features_auto(self, sample_feature_data):
        """Test automatic feature selection."""
        X, y = sample_feature_data

        selected = select_features_auto(X, y, n_features=20)

        # Note: Correlation removal may reduce the count below n_features
        assert len(selected) <= 20
        assert len(selected) > 0
        assert all(f in X.columns for f in selected)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self, feature_selector):
        """Test handling of empty DataFrame."""
        X = pd.DataFrame()
        y = pd.Series()

        # Should handle gracefully or raise informative error
        with pytest.raises(Exception):
            feature_selector.calculate_mutual_information(X, y)

    def test_single_feature(self, feature_selector):
        """Test with single feature."""
        X = pd.DataFrame({"feature_0": np.random.randn(100)})
        y = pd.Series(np.random.randn(100))

        results = feature_selector.calculate_mutual_information(X, y)

        assert len(results) == 1
        assert results[0].rank == 1

    def test_constant_feature(self, feature_selector):
        """Test with constant feature (zero variance)."""
        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.ones(100)  # Constant
        })
        y = pd.Series(np.random.randn(100))

        # Should handle gracefully
        results = feature_selector.calculate_mutual_information(X, y)

        assert len(results) == 2

    def test_perfect_correlation(self, feature_selector):
        """Test with perfectly correlated features."""
        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.random.randn(100)
        })
        X["feature_1"] = X["feature_0"]  # Perfect correlation

        pairs, to_remove = feature_selector.analyze_correlation(X, threshold=0.95)

        assert len(pairs) > 0
        assert len(to_remove) > 0

    def test_all_nan_feature(self, feature_selector):
        """Test with all-NaN feature."""
        X = pd.DataFrame({
            "feature_0": np.random.randn(100),
            "feature_1": np.full(100, np.nan)
        })
        y = pd.Series(np.random.randn(100))

        # Should handle gracefully by dropping all-NaN feature
        results = feature_selector.calculate_mutual_information(X, y)

        # All-NaN feature should be dropped
        assert len(results) == 1
        assert results[0].feature_name == "feature_0"
