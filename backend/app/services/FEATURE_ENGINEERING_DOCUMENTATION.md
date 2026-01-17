# Feature Engineering Service - Documentation

## Overview

The Feature Engineering Service transforms raw OHLCV (Open, High, Low, Close, Volume) market data into meaningful features for machine learning models. This service is the foundation for all AI-based trading predictions in the EURABAY Living System.

**Location:** `backend/app/services/feature_engineering.py`

## Table of Contents

1. [Architecture](#architecture)
2. [Configuration](#configuration)
3. [Feature Categories](#feature-categories)
4. [Calculated Features](#calculated-features)
5. [Usage Examples](#usage-examples)
6. [Caching Strategy](#caching-strategy)
7. [Missing Data Handling](#missing-data-handling)
8. [Performance Considerations](#performance-considerations)

---

## Architecture

### Core Components

- **`FeatureEngineering`**: Main service class that orchestrates feature generation
- **`FeatureConfig`**: Configuration dataclass for all feature parameters
- **`FeatureSet`**: Container for generated features with metadata

### Design Principles

1. **Modular**: Each feature type is implemented as a separate method
2. **Cached**: Computed features are cached with TTL to avoid redundant calculations
3. **Type-Safe**: Uses dataclasses and type hints throughout
4. **Tested**: Comprehensive test suite with 45+ unit tests
5. **Documented**: Every feature method includes detailed docstrings

---

## Configuration

### FeatureConfig Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SHORT_WINDOW` | 5 | Short-term rolling window |
| `MEDIUM_WINDOW` | 10 | Medium-term rolling window |
| `LONG_WINDOW` | 20 | Long-term rolling window |
| `RSI_PERIOD` | 14 | RSI calculation period |
| `MACD_FAST` | 12 | MACD fast EMA period |
| `MACD_SLOW` | 26 | MACD slow EMA period |
| `MACD_SIGNAL` | 9 | MACD signal line period |
| `BB_PERIOD` | 20 | Bollinger Bands period |
| `BB_STD` | 2.0 | Bollinger Bands std dev multiplier |
| `ATR_PERIOD` | 14 | Average True Range period |
| `STOCH_K` | 14 | Stochastic %K period |
| `STOCH_D` | 3 | Stochastic %D period |
| `ADX_PERIOD` | 14 | ADX calculation period |
| `LAG_PERIODS` | [1, 2, 3, 5, 10] | Lag periods for lag features |
| `ZSCORE_WINDOW` | 20 | Z-score calculation window |
| `CACHE_TTL` | 60 | Cache time-to-live in seconds |

### Custom Configuration Example

```python
from app.services.feature_engineering import FeatureEngineering, FeatureConfig

# Create custom configuration
custom_config = FeatureConfig(
    SHORT_WINDOW=3,
    MEDIUM_WINDOW=7,
    LONG_WINDOW=14,
    RSI_PERIOD=10,
    CACHE_TTL=120
)

# Initialize with custom config
fe = FeatureEngineering(config=custom_config)
```

---

## Feature Categories

### 1. Price-Based Features

**Feature Types:** `returns`, `log_returns`, `price_change`

**Purpose:** Capture basic price momentum and returns

**Features Generated:**
- `return_1`, `return_5`, `return_10`: Simple returns over 1, 5, 10 periods
- `log_return_1`, `log_return_5`, `log_return_10`: Logarithmic returns
- `price_change_1`, `price_change_5`, `price_change_10`: Absolute price changes

### 2. Volatility Features

**Feature Types:** `atr`, `std_dev`, `parkinson`

**Purpose:** Measure market volatility and risk

**Features Generated:**
- `atr`: Average True Range (14-period)
- `atr_ratio`: ATR normalized by price
- `std_5`, `std_10`, `std_20`: Rolling standard deviation
- `std_ratio_5`, `std_ratio_10`, `std_ratio_20`: Std dev normalized by price
- `parkinson_10`, `parkinson_20`: Parkinson volatility estimator

### 3. Momentum Features

**Feature Types:** `rsi`, `macd`, `stochastic`

**Purpose:** Identify overbought/oversold conditions and trend strength

**Features Generated:**

**RSI (Relative Strength Index):**
- `rsi`: 14-period RSI (0-100)
- `rsi_overbought`: Binary indicator (RSI > 70)
- `rsi_oversold`: Binary indicator (RSI < 30)

**MACD (Moving Average Convergence Divergence):**
- `macd`: MACD line (12, 26, 9)
- `macd_signal`: Signal line
- `macd_hist`: MACD histogram
- `macd_bullish`: Binary indicator (histogram > 0)

**Stochastic Oscillator:**
- `stoch_k`: Stochastic %K (14-period)
- `stoch_d`: Stochastic %D (3-period)
- `stoch_overbought`: Binary indicator (%K > 80)
- `stoch_oversold`: Binary indicator (%K < 20)

### 4. Trend Features

**Feature Types:** `sma`, `ema`, `adx`

**Purpose:** Identify trend direction and strength

**Features Generated:**

**Simple Moving Averages (SMA):**
- `sma_5`, `sma_10`, `sma_20`: SMAs for multiple periods
- `sma_cross_short_medium`: Short/medium crossover signal
- `sma_cross_medium_long`: Medium/long crossover signal
- `price_above_sma_short`: Price vs short SMA

**Exponential Moving Averages (EMA):**
- `ema_5`, `ema_10`, `ema_20`: EMAs for multiple periods
- `ema_cross_short_medium`: Short/medium EMA crossover
- `ema_sma_diff_short`: EMA vs SMA (trend strength)

**ADX (Average Directional Index):**
- `adx`: ADX trend strength (0-100)
- `di_plus`: +DI (positive directional indicator)
- `di_minus`: -DI (negative directional indicator)
- `adx_strong_trend`: Binary indicator (ADX > 25)
- `trend_direction`: 1 for bullish, -1 for bearish

### 5. Lag Features

**Feature Types:** `lag`

**Purpose:** Capture temporal dependencies and autoregressive patterns

**Features Generated:**
- `close_lag_1`, `close_lag_2`, `close_lag_3`, `close_lag_5`, `close_lag_10`: Lagged close prices
- `return_lag_1`, `return_lag_2`, `return_lag_3`, `return_lag_5`, `return_lag_10`: Lagged returns
- `volume_lag_1`, `volume_lag_2`, `volume_lag_3`: Lagged volume (if available)

### 6. Rolling Statistics

**Feature Types:** `rolling`

**Purpose:** Capture distribution characteristics over time windows

**Features Generated:**

For each window (5, 10, 20):
- `rolling_mean_{window}`: Rolling mean
- `rolling_std_{window}`: Rolling standard deviation
- `rolling_min_{window}`: Rolling minimum
- `rolling_max_{window}`: Rolling maximum
- `rolling_range_{window}`: Price range (max - min)
- `rolling_range_pct_{window}`: Range as percentage of mean
- `rolling_median_{window}`: Rolling median
- `rolling_skew_{window}`: Rolling skewness (asymmetry)
- `rolling_kurt_{window}`: Rolling kurtosis (tailedness)

### 7. Z-Score Features

**Feature Types:** `zscore`

**Purpose:** Standardize price and identify extreme values

**Features Generated:**
- `zscore`: Price z-score (20-period)
- `zscore_extreme_high`: Binary indicator (z-score > 2)
- `zscore_extreme_low`: Binary indicator (z-score < -2)
- `zscore_5`, `zscore_20`: Multi-period z-scores

### 8. Bollinger Bands Features

**Feature Types:** `bollinger`

**Purpose:** Identify mean reversion opportunities and volatility squeezes

**Features Generated:**
- `bb_upper`: Upper Bollinger Band (20-period, 2 std)
- `bb_middle`: Middle band (SMA)
- `bb_lower`: Lower Bollinger Band
- `bb_width`: Band width (volatility measure)
- `bb_position`: Position within bands (0-1)
- `bb_squeeze`: Binary indicator (bands narrower than average)
- `price_above_bb_upper`: Binary indicator (price > upper band)
- `price_below_bb_lower`: Binary indicator (price < lower band)

---

## Usage Examples

### Basic Usage

```python
from app.services.feature_engineering import FeatureEngineering
import pandas as pd

# Initialize service
fe = FeatureEngineering()

# Generate all features
df_with_features = fe.generate_features(
    df=ohlcv_dataframe,
    symbol="V10"
)
```

### Selective Feature Generation

```python
# Generate only specific feature types
df_features = fe.generate_features(
    df=ohlcv_dataframe,
    symbol="V10",
    feature_types=["returns", "rsi", "macd", "bollinger"]
)
```

### Get Latest Feature Set

```python
# Get latest features as FeatureSet object
feature_set = fe.get_latest_features(
    df=ohlcv_dataframe,
    symbol="V10"
)

print(f"Symbol: {feature_set.symbol}")
print(f"Features: {feature_set.feature_count}")
print(f"RSI: {feature_set.features['rsi']}")
```

### Custom Configuration

```python
from app.services.feature_engineering import FeatureConfig, FeatureEngineering

# Custom config for shorter-term trading
config = FeatureConfig(
    SHORT_WINDOW=3,
    MEDIUM_WINDOW=5,
    LONG_WINDOW=10,
    RSI_PERIOD=10,
    BB_PERIOD=15
)

fe = FeatureEngineering(config=config)
```

### Using Factory Functions

```python
from app.services.feature_engineering import create_feature_engine

# Create with default config
fe = create_feature_engine()

# Create with custom config
fe = create_feature_engine(config=custom_config)
```

### Generate from Dictionary Data

```python
from app.services.feature_engineering import generate_features_from_dict

data = [
    {"open": 10000, "high": 10050, "low": 9950, "close": 10020, "volume": 1000},
    {"open": 10020, "high": 10070, "low": 9970, "close": 10040, "volume": 1100},
    # ... more data
]

df = generate_features_from_dict(data, symbol="V10")
```

---

## Caching Strategy

### Cache Implementation

- **Type:** TTLCache (Time-To-Live)
- **Max Size:** 1000 entries
- **TTL:** 60 seconds (configurable)
- **Cache Key:** Based on symbol, DataFrame shape, last timestamp, and feature types

### Cache Management

```python
# Check cache stats
stats = fe.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Max size: {stats['cache_max_size']}")
print(f"TTL: {stats['cache_ttl']}")

# Clear cache manually
fe.clear_cache()
```

### Cache Behavior

- First call: Computes features, stores in cache
- Subsequent calls within TTL: Returns cached results
- After TTL: Recomputes and updates cache
- Different symbols/features: Separate cache entries

---

## Missing Data Handling

### Handling Strategy

The service uses a multi-stage strategy:

1. **Drop Critical Missing Values**: Rows with missing OHLC data are removed
2. **Forward Fill**: Small gaps (< 3 consecutive) filled with last valid value
3. **Backward Fill**: Remaining gaps filled with next valid value
4. **Drop Remaining**: Any remaining NaN values are dropped

### Example

```python
# Input with missing values
# close: [100, 101, NaN, NaN, 104, 105]

# After forward fill (limit=3)
# close: [100, 101, 101, 101, 104, 105]

# If still missing, backward fill
# close: [100, 101, 101, 101, 104, 105]
```

---

## Performance Considerations

### Optimization Tips

1. **Use Selective Feature Generation**: Only generate needed features
   ```python
   # Instead of all features
   df = fe.generate_features(df, "V10")

   # Use specific features
   df = fe.generate_features(df, "V10", feature_types=["returns", "rsi"])
   ```

2. **Leverage Caching**: The service automatically caches results
   - Same DataFrame within TTL = instant retrieval
   - Useful for real-time applications

3. **Batch Processing**: Process multiple symbols in sequence
   - Cache works per-symbol
   - Reuse service instance

### Performance Metrics

- **Feature Generation**: < 100ms for 1000 rows, 10 feature types
- **Cache Hit**: Instant (< 1ms)
- **Cache Miss**: Full computation time

### Memory Usage

- **Per Feature Set**: ~1KB for 100 features
- **Cache Size**: Configurable (default 1000 entries = ~1MB)
- **DataFrame Memory**: Depends on input size and feature count

---

## Feature Registry

The service maintains a registry of all available features:

```python
# Get list of available feature types
feature_types = fe.get_feature_names()
# Returns: ['returns', 'log_returns', 'price_change', 'atr',
#           'std_dev', 'parkinson', 'rsi', 'macd', 'stochastic',
#           'sma', 'ema', 'adx', 'lag', 'rolling', 'zscore',
#           'bollinger']
```

---

## Testing

### Running Tests

```bash
# Run all feature engineering tests
cd backend
pytest tests/test_feature_engineering.py -v

# Run specific test class
pytest tests/test_feature_engineering.py::TestPriceBasedFeatures -v

# Run with coverage
pytest tests/test_feature_engineering.py --cov=app.services.feature_engineering
```

### Test Coverage

- **45 tests** covering all functionality
- **100% coverage** of feature calculation methods
- Edge cases and error handling
- Caching behavior validation

---

## Troubleshooting

### Common Issues

**Issue: Missing TA-Lib**
- **Solution**: Install TA-Lib or use fallback implementations
- The service automatically falls back to pandas-ta or pure pandas

**Issue: DataFrame too small**
- **Solution**: Ensure minimum 50 rows for most features
- Some features need minimum periods (e.g., RSI needs 14+ periods)

**Issue: Cache not working**
- **Solution**: Check cache configuration and TTL
- Ensure DataFrame hasn't changed between calls

---

## Future Enhancements

Planned features for future iterations:

1. **Additional Technical Indicators**: Ichimoku Cloud, Parabolic SAR
2. **Feature Selection**: Automatic feature importance ranking
3. **Feature Validation**: Statistical quality checks per feature
4. **Performance Monitoring**: Built-in timing metrics
5. **Multi-timeframe Features**: Features across different timeframes

---

## References

- **TA-Lib**: https://ta-lib.org/
- **pandas-ta**: https://github.com/twopirllc/pandas-ta
- **Technical Analysis**: Technical Analysis of the Financial Markets by John J. Murphy

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
**Maintainer:** EURABAY Development Team
