# EURABAY Living System - Data Dictionary

## Table of Contents
1. [Introduction](#introduction)
2. [Field Types and Formats](#field-types-and-formats)
3. [Table Definitions](#table-definitions)
4. [Enum Values](#enum-values)
5. [Default Values](#default-values)
6. [JSON Field Schemas](#json-field-schemas)

---

## Introduction

This data dictionary provides detailed descriptions of all fields in the EURABAY Living System database, including data types, constraints, validation rules, and usage patterns.

---

## Field Types and Formats

### SQLite Data Types Used

| Type | Description | Example Values |
|------|-------------|----------------|
| INTEGER | Whole numbers | 1, 42, 1000 |
| REAL | Floating-point numbers | 1.2345, 0.95, -42.5 |
| TEXT | String values | 'BUY', 'V10', 'strategy_name' |
| DATETIME | Timestamp (ISO 8601 stored as TEXT) | '2025-01-17 10:30:00' |
| BOOLEAN | Integer 0 or 1 | 0 (false), 1 (true) |

### Special Formats

| Field | Format | Example |
|-------|--------|---------|
| Timestamps | ISO 8601 | `2025-01-17T10:30:00` |
| Symbols | Uppercase with optional number | `V10`, `V25`, `V50`, `V75`, `V100` |
| Directions | Uppercase | `BUY`, `SELL`, `WAIT` |
| Status | Uppercase | `OPEN`, `CLOSED`, `PENDING` |
| Confidence | Decimal 0-1 | `0.85`, `0.95`, `0.50` |

---

## Table Definitions

### trades

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| mt5_ticket | INTEGER | YES | NULL | MT5 platform ticket number (must be unique if provided) |
| symbol | VARCHAR(10) | NO | | Trading symbol (e.g., V10, V25) |
| direction | VARCHAR(4) | NO | | Trade direction: 'BUY' or 'SELL' |
| entry_price | REAL | NO | | Price at which trade was entered |
| entry_time | DATETIME | NO | CURRENT_TIMESTAMP | UTC timestamp when trade was entered |
| exit_price | REAL | YES | NULL | Price at which trade was exited (NULL if open) |
| exit_time | DATETIME | YES | NULL | UTC timestamp when trade was exited (NULL if open) |
| stop_loss | REAL | YES | NULL | Stop loss price level |
| take_profit | REAL | YES | NULL | Take profit price level |
| lot_size | REAL | NO | | Position size in standard lots |
| confidence | REAL | NO | | Signal confidence (0.0 to 1.0) |
| strategy_used | VARCHAR(100) | NO | | Name of strategy that generated the trade |
| profit_loss | REAL | YES | NULL | Profit/loss in account currency (calculated after exit) |
| profit_loss_pips | REAL | YES | NULL | Profit/loss in pips (calculated after exit) |
| status | VARCHAR(10) | NO | 'OPEN' | Current status: 'OPEN', 'CLOSED', 'PENDING' |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | Last update timestamp (auto-updated by trigger) |

**Validation Rules**:
- `direction` must be 'BUY' or 'SELL'
- `status` must be 'OPEN', 'CLOSED', or 'PENDING'
- `confidence` must be between 0.0 and 1.0
- `mt5_ticket` must be unique if provided
- `entry_price` must be greater than 0
- `lot_size` must be greater than 0

---

### performance_metrics

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| period | VARCHAR(20) | NO | | Period type: 'daily', 'weekly', 'monthly', 'all_time' |
| period_start | DATETIME | NO | | Start of period (UTC) |
| period_end | DATETIME | NO | | End of period (UTC) |
| total_trades | INTEGER | NO | 0 | Total number of trades in period |
| winning_trades | INTEGER | NO | 0 | Number of profitable trades |
| losing_trades | INTEGER | NO | 0 | Number of unprofitable trades |
| win_rate | REAL | NO | 0 | Percentage of winning trades (0-100) |
| total_profit | REAL | NO | 0 | Sum of all profitable trade amounts |
| total_loss | REAL | NO | 0 | Sum of all unprofitable trade amounts (absolute value) |
| profit_factor | REAL | NO | 0 | Ratio: total_profit / total_loss |
| average_win | REAL | NO | 0 | Average profit from winning trades |
| average_loss | REAL | NO | 0 | Average loss from losing trades |
| max_drawdown | REAL | NO | 0 | Maximum drawdown amount in period |
| max_drawdown_pct | REAL | NO | 0 | Maximum drawdown as percentage |
| sharpe_ratio | REAL | YES | NULL | Risk-adjusted return metric (annualized) |
| sortino_ratio | REAL | YES | NULL | Downside risk-adjusted return metric |
| calmar_ratio | REAL | YES | NULL | Return/max drawdown ratio |
| equity_curve | TEXT | YES | NULL | JSON array of equity values over time |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | Last update timestamp (auto-updated by trigger) |

**Validation Rules**:
- `period` must be 'daily', 'weekly', 'monthly', or 'all_time'
- `win_rate` must be between 0 and 100
- `total_trades` = `winning_trades` + `losing_trades`
- `profit_factor` = `total_profit` / `total_loss` (when total_loss > 0)
- `equity_curve` must be valid JSON array if provided

**Calculated Fields**:
```
win_rate = (winning_trades / total_trades) * 100
profit_factor = total_profit / total_loss
average_win = total_profit / winning_trades
average_loss = total_loss / losing_trades
```

---

### models

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| model_name | VARCHAR(100) | NO | | Human-readable model name |
| model_type | VARCHAR(50) | NO | | Model type: 'CLASSIFIER', 'REGRESSION', etc. |
| model_version | VARCHAR(50) | NO | | Version identifier (e.g., 'v1.0.0') |
| symbol | VARCHAR(10) | NO | | Symbol this model was trained for |
| training_samples | INTEGER | NO | | Number of samples used for training |
| features_used | TEXT | NO | | JSON array of feature names used |
| file_path | VARCHAR(500) | NO | | Path to saved model file (relative or absolute) |
| accuracy | REAL | NO | | Model accuracy score (0.0 to 1.0) |
| precision | REAL | NO | | Model precision score (0.0 to 1.0) |
| recall | REAL | NO | | Model recall score (0.0 to 1.0) |
| f1_score | REAL | NO | | F1 score - harmonic mean of precision and recall |
| is_active | BOOLEAN | NO | 1 | Whether this model is currently in use |
| training_time | DATETIME | NO | CURRENT_TIMESTAMP | When model training completed |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | Last update timestamp (auto-updated by trigger) |

**Validation Rules**:
- All metric scores (`accuracy`, `precision`, `recall`, `f1_score`) must be between 0.0 and 1.0
- `features_used` must be valid JSON array
- `file_path` must point to an existing file when `is_active = 1`

---

### configurations

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| config_key | VARCHAR(100) | NO | UNIQUE | Configuration key name (dot notation preferred) |
| config_value | TEXT | NO | | Configuration value (JSON or string) |
| description | VARCHAR(500) | NO | | Human-readable description of what this controls |
| category | VARCHAR(50) | NO | | Category: 'risk', 'trading', 'system', etc. |
| is_active | BOOLEAN | NO | 1 | Whether this configuration is currently active |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | Last update timestamp (auto-updated by trigger) |

**Common Configuration Keys**:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| risk.max_position_risk_pct | REAL | 2.0 | Maximum risk per position as percentage |
| risk.max_daily_loss_pct | REAL | 5.0 | Maximum daily loss as percentage |
| risk.max_concurrent_positions | INTEGER | 3 | Maximum number of concurrent trades |
| trading.symbols | JSON ARRAY | ["V10",...] | List of tradeable symbols |
| trading.min_signal_confidence | REAL | 0.6 | Minimum confidence to execute signal |
| trading.paper_trading_mode | BOOLEAN | true | Paper trading mode flag |
| system.loop_interval | INTEGER | 1 | Main loop interval in seconds |

---

### market_data

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| symbol | VARCHAR(10) | NO | | Trading symbol |
| timeframe | VARCHAR(10) | NO | | Timeframe: 'M1', 'M5', 'M15', 'H1', 'H4', 'D1' |
| timestamp | DATETIME | NO | | Price timestamp (UTC) |
| open_price | REAL | NO | | Opening price of candle |
| high_price | REAL | NO | | Highest price of candle |
| low_price | REAL | NO | | Lowest price of candle |
| close_price | REAL | NO | | Closing price of candle |
| volume | INTEGER | NO | 0 | Trading volume |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |

**Validation Rules**:
- `high_price` >= `low_price`
- `high_price` >= `open_price`
- `high_price` >= `close_price`
- `low_price` <= `open_price`
- `low_price` <= `close_price`
- All prices must be greater than 0

**Timeframe Values**:
- `M1`: 1 minute
- `M5`: 5 minutes
- `M15`: 15 minutes
- `M30`: 30 minutes
- `H1`: 1 hour
- `H4`: 4 hours
- `D1`: 1 day

---

### signals

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| symbol | VARCHAR(10) | NO | | Trading symbol |
| direction | VARCHAR(10) | NO | | Signal direction: 'BUY', 'SELL', 'WAIT' |
| confidence | REAL | NO | | Signal confidence (0.0 to 1.0) |
| price | REAL | NO | | Price at signal generation |
| strategy | VARCHAR(100) | NO | | Strategy that generated the signal |
| reasons | TEXT | YES | NULL | JSON array of reasons for the signal |
| timestamp | DATETIME | NO | CURRENT_TIMESTAMP | Signal generation timestamp (UTC) |
| executed | BOOLEAN | NO | 0 | Whether signal was executed into a trade |
| trade_id | INTEGER | YES | NULL | Foreign key to trades.id if executed |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |

**Validation Rules**:
- `direction` must be 'BUY', 'SELL', or 'WAIT'
- `confidence` must be between 0.0 and 1.0
- `reasons` must be valid JSON array if provided
- If `executed = 1`, `trade_id` should be set
- `trade_id` references `trades.id` (SET NULL on delete)

---

### system_logs

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| timestamp | DATETIME | NO | CURRENT_TIMESTAMP | Log timestamp (UTC) |
| level | VARCHAR(20) | NO | | Log level (see enum values below) |
| message | TEXT | NO | | Log message |
| context | TEXT | YES | NULL | JSON object with additional context |
| source | VARCHAR(100) | YES | NULL | Source component or module |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | Record creation timestamp |

**Validation Rules**:
- `level` must be valid log level
- `context` must be valid JSON object if provided

---

### schema_migrations

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | INTEGER | NO | AUTO | Unique identifier (Primary Key) |
| version | VARCHAR(20) | NO | UNIQUE | Migration version (e.g., '001', '002') |
| description | TEXT | YES | NULL | Human-readable migration description |
| applied_at | DATETIME | NO | CURRENT_TIMESTAMP | When migration was applied (UTC) |
| execution_time_ms | INTEGER | YES | NULL | Execution time in milliseconds |

---

## Enum Values

### trades.direction

| Value | Description |
|-------|-------------|
| BUY | Long position |
| SELL | Short position |

### trades.status

| Value | Description |
|-------|-------------|
| OPEN | Trade is currently active |
| CLOSED | Trade has been exited |
| PENDING | Trade is pending execution |

### performance_metrics.period

| Value | Description |
|-------|-------------|
| daily | Metrics for a single day |
| weekly | Metrics for a week |
| monthly | Metrics for a month |
| all_time | Metrics from beginning to current date |

### models.model_type

| Value | Description |
|-------|-------------|
| CLASSIFIER | Binary/multi-class classification model |
| REGRESSION | Regression model for continuous predictions |
| ENSEMBLE | Ensemble of multiple models |
| NEURAL_NETWORK | Deep learning model |
| TIMESERIES | Time-series specific model |

### signals.direction

| Value | Description |
|-------|-------------|
| BUY | Buy signal |
| SELL | Sell signal |
| WAIT | Wait/hold signal |

### system_logs.level

| Value | Description | Use Case |
|-------|-------------|----------|
| DEBUG | Detailed debugging information | Development troubleshooting |
| INFO | General informational messages | Normal operation tracking |
| WARNING | Warning messages | Potential issues that need attention |
| ERROR | Error messages | Errors that don't stop execution |
| CRITICAL | Critical errors | Errors that stop execution |

### configurations.category

| Value | Description |
|-------|-------------|
| risk | Risk management settings |
| trading | Trading behavior settings |
| system | System operation settings |
| strategy | Strategy-specific settings |
| ml | Machine learning settings |
| database | Database configuration |

### market_data.timeframe

| Value | Description |
|-------|-------------|
| M1 | 1 minute candle |
| M5 | 5 minute candle |
| M15 | 15 minute candle |
| M30 | 30 minute candle |
| H1 | 1 hour candle |
| H4 | 4 hour candle |
| D1 | 1 day candle |

---

## Default Values

### Auto-Generated Timestamps

The following fields default to `CURRENT_TIMESTAMP`:
- `trades.entry_time`
- `trades.created_at`
- `trades.updated_at`
- `performance_metrics.created_at`
- `performance_metrics.updated_at`
- `models.training_time`
- `models.created_at`
- `models.updated_at`
- `configurations.created_at`
- `configurations.updated_at`
- `market_data.created_at`
- `signals.timestamp`
- `signals.created_at`
- `system_logs.timestamp`
- `system_logs.created_at`
- `schema_migrations.applied_at`

### Numeric Defaults

| Table | Field | Default |
|-------|-------|---------|
| performance_metrics | total_trades | 0 |
| performance_metrics | winning_trades | 0 |
| performance_metrics | losing_trades | 0 |
| performance_metrics | win_rate | 0 |
| performance_metrics | total_profit | 0 |
| performance_metrics | total_loss | 0 |
| performance_metrics | profit_factor | 0 |
| performance_metrics | average_win | 0 |
| performance_metrics | average_loss | 0 |
| performance_metrics | max_drawdown | 0 |
| performance_metrics | max_drawdown_pct | 0 |
| models | is_active | 1 |
| market_data | volume | 0 |
| signals | executed | 0 |

### String Defaults

| Table | Field | Default |
|-------|-------|---------|
| trades | status | 'OPEN' |

---

## JSON Field Schemas

### features_used (models table)

Array of feature names:
```json
[
  "rsi_14",
  "macd_signal",
  "bb_upper",
  "bb_lower",
  "volume_ratio",
  "price_momentum"
]
```

### equity_curve (performance_metrics table)

Array of equity values over time:
```json
[
  {"timestamp": "2025-01-17T00:00:00", "equity": 10000.00},
  {"timestamp": "2025-01-17T01:00:00", "equity": 10050.00},
  {"timestamp": "2025-01-17T02:00:00", "equity": 10020.00}
]
```

### config_value (configurations table)

Can be various types:

**Boolean**:
```json
true
```

**Number**:
```json
2.5
```

**Array**:
```json
["V10", "V25", "V50", "V75", "V100"]
```

**Object**:
```json
{
  "enabled": true,
  "threshold": 0.8,
  "symbols": ["V10", "V25"]
}
```

### reasons (signals table)

Array of reason objects:
```json
[
  {"type": "indicator", "name": "RSI", "value": 25, "condition": "oversold"},
  {"type": "indicator", "name": "MACD", "value": 0.002, "condition": "crossover"},
  {"type": "pattern", "name": "engulfing", "bullish": true}
]
```

### context (system_logs table)

Object with additional context:
```json
{
  "module": "trading_engine",
  "function": "execute_trade",
  "trade_id": 123,
  "error_code": "INSUFFICIENT_BALANCE"
}
```

---

## Field Relationships

### Related Field Pairs

| Table 1 | Field 1 | Table 2 | Field 2 | Relationship |
|---------|---------|---------|---------|--------------|
| trades | id | signals | trade_id | One-to-Many |

### Composite Keys (Implied)

| Table | Fields | Unique Together |
|-------|--------|-----------------|
| market_data | symbol, timeframe, timestamp | Yes (natural key) |

---

## Data Integrity Rules

### Business Rules

1. **Trade Lifecycle**:
   - Trade starts with `status = 'OPEN'` and `exit_price = NULL`
   - On close: `status = 'CLOSED'`, `exit_price` and `exit_time` set
   - `profit_loss` and `profit_loss_pips` calculated on close

2. **Signal to Trade**:
   - Signal created with `executed = 0`
   - If executed: `executed = 1`, `trade_id` set to corresponding `trades.id`

3. **Performance Metrics**:
   - `total_trades = winning_trades + losing_trades`
   - `win_rate = (winning_trades / total_trades) * 100`
   - Updated when trades close

4. **Model Activation**:
   - Only one model per symbol should be `is_active = 1` at a time
   - New model activation should deactivate old model

5. **Market Data Uniqueness**:
   - Combination of `symbol + timeframe + timestamp` should be unique
   - Use `INSERT OR REPLACE` for upserts

---

## Index Usage Guidelines

### When to Use Indexes

| Query Pattern | Use Index |
|---------------|-----------|
| Get trades by symbol | `ix_trades_symbol` |
| Get open trades | `ix_trades_status` |
| Recent trades by time | `ix_trades_entry_time` |
| Active trades for symbol | `ix_trades_symbol_status` |
| Signals by symbol and time | `ix_signals_symbol_timestamp` |
| Market data for backtesting | `ix_market_data_symbol_timeframe_timestamp` |
| Logs by time and level | `ix_system_logs_timestamp_level` |
| Active models by symbol | `ix_models_symbol_active` |

---

## Data Retention

| Data Type | Retention Period | Cleanup Method |
|-----------|------------------|----------------|
| Market data (SQLite) | 90 days | Automated cleanup |
| Market data (Parquet) | Configurable | Manual archive |
| System logs | 30 days | Automated cleanup |
| Trade history | Permanent | No cleanup |
| Performance metrics | Permanent | No cleanup |
| Signals | 90 days | Automated cleanup |

---

## Next Steps

- See [Database Schema](./database-schema.md) for complete schema documentation
- See [Query Patterns](./query-patterns.md) for common query examples
- See [Backup and Restore](./backup-restore.md) for disaster recovery procedures
