# EURABAY Living System - Database Schema Documentation

## Table of Contents
1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Core Tables](#core-tables)
4. [Indexes](#indexes)
5. [Foreign Keys and Relationships](#foreign-keys-and-relationships)
6. [Views](#views)
7. [Triggers](#triggers)
8. [Constraints](#constraints)

---

## Overview

The EURABAY Living System uses **SQLite 3** with **async support via aiosqlite 0.19+** as its primary database. The database is stored locally at `backend/data/eurabay_trading.db` and implements a comprehensive schema for trading operations, performance tracking, ML model management, and system configuration.

### Key Technical Details
- **Database Engine**: SQLite 3
- **Async Support**: aiosqlite 0.19+
- **ORM**: SQLAlchemy 2.0+
- **Connection Pooling**: Configurable pool size (default: 5)
- **Default Location**: `backend/data/eurabay_trading.db`

---

## Entity Relationship Diagram

```mermaid
erDiagram
    TRADES ||--o{ SIGNALS : "has"
    TRADES {
        integer id PK
        integer mt5_ticket UNIQUE
        varchar symbol
        varchar direction
        real entry_price
        datetime entry_time
        real exit_price
        datetime exit_time
        real stop_loss
        real take_profit
        real lot_size
        real confidence
        varchar strategy_used
        real profit_loss
        real profit_loss_pips
        varchar status
        datetime created_at
        datetime updated_at
    }

    SIGNALS {
        integer id PK
        varchar symbol
        varchar direction
        real confidence
        real price
        varchar strategy
        text reasons
        datetime timestamp
        boolean executed
        integer trade_id FK
        datetime created_at
    }

    PERFORMANCE_METRICS {
        integer id PK
        varchar period
        datetime period_start
        datetime period_end
        integer total_trades
        integer winning_trades
        integer losing_trades
        real win_rate
        real total_profit
        real total_loss
        real profit_factor
        real average_win
        real average_loss
        real max_drawdown
        real max_drawdown_pct
        real sharpe_ratio
        real sortino_ratio
        real calmar_ratio
        text equity_curve
        datetime created_at
        datetime updated_at
    }

    MODELS {
        integer id PK
        varchar model_name
        varchar model_type
        varchar model_version
        varchar symbol
        integer training_samples
        text features_used
        varchar file_path
        real accuracy
        real precision
        real recall
        real f1_score
        boolean is_active
        datetime training_time
        datetime created_at
        datetime updated_at
    }

    CONFIGURATIONS {
        integer id PK
        varchar config_key UNIQUE
        text config_value
        text description
        varchar category
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    MARKET_DATA {
        integer id PK
        varchar symbol
        varchar timeframe
        datetime timestamp
        real open_price
        real high_price
        real low_price
        real close_price
        integer volume
        datetime created_at
    }

    SYSTEM_LOGS {
        integer id PK
        datetime timestamp
        varchar level
        text message
        text context
        varchar source
        datetime created_at
    }

    TRADES ||--o{ SIGNALS : "generates"
```

---

## Core Tables

### 1. trades

**Purpose**: Stores all trading activity including entries, exits, and performance metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique trade identifier |
| mt5_ticket | INTEGER | UNIQUE | MT5 platform ticket number |
| symbol | VARCHAR(10) | NOT NULL | Trading symbol (e.g., V10, V25) |
| direction | VARCHAR(4) | NOT NULL, CHECK | Trade direction: BUY or SELL |
| entry_price | REAL | NOT NULL | Entry price |
| entry_time | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Trade entry timestamp |
| exit_price | REAL | | Exit price (NULL when open) |
| exit_time | DATETIME | | Exit timestamp (NULL when open) |
| stop_loss | REAL | | Stop loss price |
| take_profit | REAL | | Take profit price |
| lot_size | REAL | NOT NULL | Position size in lots |
| confidence | REAL | NOT NULL, CHECK | Signal confidence (0.0 to 1.0) |
| strategy_used | VARCHAR(100) | NOT NULL | Strategy that generated the trade |
| profit_loss | REAL | | Profit/loss in account currency |
| profit_loss_pips | REAL | | Profit/loss in pips |
| status | VARCHAR(10) | NOT NULL, CHECK | Trade status: OPEN, CLOSED, PENDING |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Constraints**:
```sql
CHECK (direction IN ('BUY', 'SELL'))
CHECK (status IN ('OPEN', 'CLOSED', 'PENDING'))
CHECK (confidence >= 0 AND confidence <= 1)
```

**Typical Use Cases**:
- Track all trading operations
- Calculate performance metrics
- Audit trail for trades
- Link to MT5 platform via mt5_ticket

---

### 2. performance_metrics

**Purpose**: Stores aggregated performance metrics for different time periods.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique metric identifier |
| period | VARCHAR(20) | NOT NULL, CHECK | Period type: daily, weekly, monthly, all_time |
| period_start | DATETIME | NOT NULL | Period start timestamp |
| period_end | DATETIME | NOT NULL | Period end timestamp |
| total_trades | INTEGER | NOT NULL, DEFAULT 0 | Total number of trades |
| winning_trades | INTEGER | NOT NULL, DEFAULT 0 | Number of winning trades |
| losing_trades | INTEGER | NOT NULL, DEFAULT 0 | Number of losing trades |
| win_rate | REAL | NOT NULL, DEFAULT 0 | Win rate percentage (0-100) |
| total_profit | REAL | NOT NULL, DEFAULT 0 | Total profit from winning trades |
| total_loss | REAL | NOT NULL, DEFAULT 0 | Total loss from losing trades |
| profit_factor | REAL | NOT NULL, DEFAULT 0 | Profit factor (total_profit / total_loss) |
| average_win | REAL | NOT NULL, DEFAULT 0 | Average winning trade amount |
| average_loss | REAL | NOT NULL, DEFAULT 0 | Average losing trade amount |
| max_drawdown | REAL | NOT NULL, DEFAULT 0 | Maximum drawdown amount |
| max_drawdown_pct | REAL | NOT NULL, DEFAULT 0 | Maximum drawdown percentage |
| sharpe_ratio | REAL | | Sharpe ratio |
| sortino_ratio | REAL | | Sortino ratio |
| calmar_ratio | REAL | | Calmar ratio |
| equity_curve | TEXT | | JSON serialized equity curve data |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Constraints**:
```sql
CHECK (win_rate >= 0 AND win_rate <= 100)
CHECK (period IN ('daily', 'weekly', 'monthly', 'all_time'))
```

**Typical Use Cases**:
- Track performance over different time periods
- Generate performance reports
- Calculate risk-adjusted returns
- Monitor drawdown levels

---

### 3. models

**Purpose**: Stores ML model metadata, performance metrics, and file locations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique model identifier |
| model_name | VARCHAR(100) | NOT NULL | Name of the model |
| model_type | VARCHAR(50) | NOT NULL | Type: CLASSIFIER, REGRESSION, etc. |
| model_version | VARCHAR(50) | NOT NULL | Version identifier |
| symbol | VARCHAR(10) | NOT NULL | Symbol this model is for |
| training_samples | INTEGER | NOT NULL | Number of training samples used |
| features_used | TEXT | NOT NULL | JSON array of feature names |
| file_path | VARCHAR(500) | NOT NULL | Path to saved model file |
| accuracy | REAL | NOT NULL, CHECK | Model accuracy (0.0 to 1.0) |
| precision | REAL | NOT NULL, CHECK | Model precision (0.0 to 1.0) |
| recall | REAL | NOT NULL, CHECK | Model recall (0.0 to 1.0) |
| f1_score | REAL | NOT NULL, CHECK | Model F1 score (0.0 to 1.0) |
| is_active | BOOLEAN | NOT NULL, DEFAULT 1 | Whether model is active |
| training_time | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When model was trained |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Constraints**:
```sql
CHECK (accuracy >= 0 AND accuracy <= 1)
CHECK (precision >= 0 AND precision <= 1)
CHECK (recall >= 0 AND recall <= 1)
CHECK (f1_score >= 0 AND f1_score <= 1)
```

**Typical Use Cases**:
- Track ML model versions and performance
- Manage model lifecycle (activation/deactivation)
- Link models to trading strategies
- Store feature engineering information

---

### 4. configurations

**Purpose**: Stores runtime configuration that can be updated without code changes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique configuration identifier |
| config_key | VARCHAR(100) | NOT NULL, UNIQUE | Configuration key name |
| config_value | TEXT | NOT NULL | Configuration value (JSON or string) |
| description | VARCHAR(500) | NOT NULL | Human-readable description |
| category | VARCHAR(50) | NOT NULL | Configuration category |
| is_active | BOOLEAN | NOT NULL, DEFAULT 1 | Whether configuration is active |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Typical Use Cases**:
- Store risk management parameters
- Store trading settings
- Store system settings
- Enable/disable features without redeployment

---

### 5. market_data

**Purpose**: Stores OHLCV price data for historical analysis and feature engineering.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique data identifier |
| symbol | VARCHAR(10) | NOT NULL | Trading symbol |
| timeframe | VARCHAR(10) | NOT NULL | Timeframe: M1, M5, M15, H1, etc. |
| timestamp | DATETIME | NOT NULL | Price timestamp |
| open_price | REAL | NOT NULL | Opening price |
| high_price | REAL | NOT NULL | Highest price |
| low_price | REAL | NOT NULL | Lowest price |
| close_price | REAL | NOT NULL | Closing price |
| volume | INTEGER | NOT NULL, DEFAULT 0 | Trading volume |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Constraints**:
```sql
CHECK (high_price >= low_price)
CHECK (high_price >= open_price)
CHECK (high_price >= close_price)
CHECK (low_price <= open_price)
CHECK (low_price <= close_price)
```

**Typical Use Cases**:
- Historical price data storage
- Feature engineering for ML models
- Backtesting strategies
- Technical analysis calculations

**Note**: For large-scale time-series data, use the Parquet-based storage system in `backend/storage/time_series_storage.py` which provides better compression and query performance.

---

### 6. signals

**Purpose**: Stores all trading signals generated by the system for audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique signal identifier |
| symbol | VARCHAR(10) | NOT NULL | Trading symbol |
| direction | VARCHAR(10) | NOT NULL, CHECK | Signal direction: BUY, SELL, WAIT |
| confidence | REAL | NOT NULL, CHECK | Signal confidence (0.0 to 1.0) |
| price | REAL | NOT NULL | Price at signal generation |
| strategy | VARCHAR(100) | NOT NULL | Strategy that generated signal |
| reasons | TEXT | | JSON array of reasons for signal |
| timestamp | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Signal generation timestamp |
| executed | BOOLEAN | NOT NULL, DEFAULT 0 | Whether signal was executed |
| trade_id | INTEGER | FK | Link to trades table if executed |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Constraints**:
```sql
CHECK (direction IN ('BUY', 'SELL', 'WAIT'))
CHECK (confidence >= 0 AND confidence <= 1)
FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE SET NULL
```

**Typical Use Cases**:
- Audit trail for all signals
- Debug strategy behavior
- Analyze signal execution rate
- Track signal-to-trade conversion

---

### 7. system_logs

**Purpose**: Stores system logs for debugging and monitoring.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique log identifier |
| timestamp | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Log timestamp |
| level | VARCHAR(20) | NOT NULL, CHECK | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| message | TEXT | NOT NULL | Log message |
| context | TEXT | | JSON context data |
| source | VARCHAR(100) | | Source component |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Constraints**:
```sql
CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
```

**Typical Use Cases**:
- Debugging system behavior
- Monitoring system health
- Audit trail for critical operations
- Performance analysis

---

### 8. schema_migrations

**Purpose**: Tracks applied database migrations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique migration record |
| version | VARCHAR(20) | NOT NULL, UNIQUE | Migration version (e.g., 001, 002) |
| description | TEXT | | Migration description |
| applied_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When migration was applied |
| execution_time_ms | INTEGER | | Execution time in milliseconds |

**Typical Use Cases**:
- Track schema evolution
- Enable migration rollback
- Audit schema changes
- Ensure migration order

---

## Indexes

### trades Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_trades_symbol | symbol | Single | Fast symbol lookups |
| ix_trades_status | status | Single | Filter open/closed trades |
| ix_trades_entry_time | entry_time | Single | Time-based queries |
| ix_trades_exit_time | exit_time | Single | Exit time queries |
| ix_trades_symbol_status | symbol, status | Composite | Active trades for symbol |
| ix_trades_status_entry_time | status, entry_time | Composite | Recent trades by status |
| ix_trades_entry_time_exit_time | entry_time, exit_time | Composite | Date range queries |
| ix_trades_symbol_entry_time_status | symbol, entry_time, status | Composite | Symbol-specific time queries |
| ix_trades_mt5_ticket | mt5_ticket | Single | MT5 ticket lookups |
| ix_trades_covering_active | status, entry_time, symbol, direction, entry_price, stop_loss, take_profit, lot_size, confidence | Partial Index | Covering index for active trades |

### performance_metrics Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_performance_period | period | Single | Filter by period type |
| ix_performance_period_start | period_start | Single | Time-based queries |
| ix_performance_period_end | period_end | Single | Time-based queries |
| ix_performance_metrics_period | period, period_start, period_end | Composite | Period range queries |
| ix_performance_period_start_end | period_start, period_end | Composite | Date range queries |

### models Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_models_model_name | model_name | Single | Model name lookups |
| ix_models_symbol | symbol | Single | Symbol-specific models |
| ix_models_is_active | is_active | Single | Active model queries |
| ix_models_symbol_active | symbol, is_active | Composite | Active models by symbol |
| ix_models_name_version | model_name, model_version | Composite | Model version lookups |
| ix_models_training_time | training_time | Single | Time-based queries |
| ix_models_symbol_active_training_time | symbol, is_active, training_time | Composite | Recent active models |
| ix_models_active_training_time | is_active, training_time | Composite | Recent active models |

### configurations Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_config_config_key | config_key | Single | Fast key lookups |
| ix_config_category | category | Single | Category-based queries |

### market_data Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_market_data_symbol | symbol | Single | Symbol-based queries |
| ix_market_data_timeframe | timeframe | Single | Timeframe filtering |
| ix_market_data_timestamp | timestamp | Single | Time-based queries |
| ix_market_data_symbol_timeframe_timestamp | symbol, timeframe, timestamp | Composite | Main query pattern |
| ix_market_data_timestamp_symbol | timestamp, symbol | Composite | Time-based with symbol |

### signals Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_signals_symbol | symbol | Single | Symbol-based queries |
| ix_signals_direction | direction | Single | Direction filtering |
| ix_signals_timestamp | timestamp | Single | Time-based queries |
| ix_signals_symbol_timestamp | symbol, timestamp | Composite | Symbol + time queries |
| ix_signals_executed | executed | Single | Executed status filtering |
| ix_signals_executed_timestamp | executed, timestamp | Composite | Recent unexecuted signals |
| ix_signals_symbol_executed_timestamp | symbol, executed, timestamp | Composite | Symbol-specific unexecuted |
| ix_signals_timestamp_executed_symbol | timestamp, executed, symbol | Composite | Time-based unexecuted |
| ix_signals_trade_id | trade_id | Single | Foreign key lookups |
| ix_signals_covering_unexecuted | executed, timestamp, symbol, direction | Partial Index | Covering for unexecuted signals |

### system_logs Table Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| ix_system_logs_timestamp | timestamp | Single | Time-based queries |
| ix_system_logs_level | level | Single | Log level filtering |
| ix_system_logs_source | source | Single | Source-based queries |
| ix_system_logs_timestamp_level | timestamp, level | Composite | Time + level queries |
| ix_system_logs_timestamp_level_source | timestamp, level, source | Composite | Filtered log queries |

---

## Foreign Keys and Relationships

### Foreign Key Constraints

| Child Table | Child Column | Parent Table | Parent Column | On Delete |
|-------------|--------------|--------------|---------------|-----------|
| signals | trade_id | trades | id | SET NULL |

**Relationships**:
- **One-to-Many**: One trade can have multiple signals
- When a trade is deleted, associated signals keep their record but `trade_id` is set to NULL

---

## Views

### 1. v_active_trades

**Purpose**: Provides active trades with calculated stop loss and take profit distances.

```sql
CREATE VIEW v_active_trades AS
SELECT
    id, mt5_ticket, symbol, direction, entry_price, entry_time,
    stop_loss, take_profit, lot_size, confidence, strategy_used,
    profit_loss, profit_loss_pips, status, created_at, updated_at,
    datetime(entry_time) as entry_datetime,
    CASE
        WHEN direction = 'BUY' THEN entry_price - stop_loss
        ELSE stop_loss - entry_price
    END as stop_loss_distance,
    CASE
        WHEN direction = 'BUY' THEN take_profit - entry_price
        ELSE entry_price - take_profit
    END as take_profit_distance
FROM trades
WHERE status = 'OPEN'
ORDER BY entry_time DESC;
```

**Use Case**: Quick access to currently open trades with risk metrics.

---

### 2. v_performance_summary

**Purpose**: Summarizes performance metrics ordered by period.

```sql
CREATE VIEW v_performance_summary AS
SELECT
    period, period_start, period_end, total_trades, winning_trades,
    losing_trades, win_rate, total_profit, total_loss, profit_factor,
    average_win, average_loss, max_drawdown, max_drawdown_pct, sharpe_ratio
FROM performance_metrics
ORDER BY period_start DESC;
```

**Use Case**: Performance dashboard and reporting.

---

### 3. v_active_models

**Purpose**: Lists currently active ML models.

```sql
CREATE VIEW v_active_models AS
SELECT
    id, model_name, model_type, model_version, symbol, accuracy,
    precision, recall, f1_score, training_time,
    datetime(training_time) as training_datetime
FROM models
WHERE is_active = 1
ORDER BY training_time DESC;
```

**Use Case**: View which models are currently in use.

---

### 4. v_recent_signals

**Purpose**: Shows signals from the last 24 hours.

```sql
CREATE VIEW v_recent_signals AS
SELECT
    id, symbol, direction, confidence, price, strategy, timestamp,
    executed, trade_id, datetime(timestamp) as signal_datetime
FROM signals
WHERE timestamp >= datetime('now', '-24 hours')
ORDER BY timestamp DESC;
```

**Use Case**: Recent signal dashboard and monitoring.

---

## Triggers

### Automatic Timestamp Update Triggers

Each of the following triggers automatically updates the `updated_at` column when a record is modified:

#### 1. update_trades_timestamp
```sql
CREATE TRIGGER update_trades_timestamp
AFTER UPDATE ON trades
FOR EACH ROW
BEGIN
    UPDATE trades SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
```

#### 2. update_performance_metrics_timestamp
```sql
CREATE TRIGGER update_performance_metrics_timestamp
AFTER UPDATE ON performance_metrics
FOR EACH ROW
BEGIN
    UPDATE performance_metrics SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
```

#### 3. update_models_timestamp
```sql
CREATE TRIGGER update_models_timestamp
AFTER UPDATE ON models
FOR EACH ROW
BEGIN
    UPDATE models SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
```

#### 4. update_configurations_timestamp
```sql
CREATE TRIGGER update_configurations_timestamp
AFTER UPDATE ON configurations
FOR EACH ROW
BEGIN
    UPDATE configurations SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
```

---

## Constraints Summary

### CHECK Constraints

| Table | Column | Constraint |
|-------|--------|------------|
| trades | direction | IN ('BUY', 'SELL') |
| trades | status | IN ('OPEN', 'CLOSED', 'PENDING') |
| trades | confidence | 0.0 to 1.0 |
| performance_metrics | win_rate | 0 to 100 |
| performance_metrics | period | IN ('daily', 'weekly', 'monthly', 'all_time') |
| models | accuracy | 0.0 to 1.0 |
| models | precision | 0.0 to 1.0 |
| models | recall | 0.0 to 1.0 |
| models | f1_score | 0.0 to 1.0 |
| signals | direction | IN ('BUY', 'SELL', 'WAIT') |
| signals | confidence | 0.0 to 1.0 |
| system_logs | level | IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') |
| market_data | high_price | >= low_price |
| market_data | high_price | >= open_price |
| market_data | high_price | >= close_price |
| market_data | low_price | <= open_price |
| market_data | low_price | <= close_price |

### UNIQUE Constraints

| Table | Column(s) |
|-------|-----------|
| trades | mt5_ticket |
| configurations | config_key |
| schema_migrations | version |

---

## Database File Locations

| File | Location |
|------|----------|
| Main Database | `backend/data/eurabay_trading.db` |
| Backups | `backend/backups/` |
| Parquet Storage | `backend/data/market/{symbol}/{YYYY-MM-DD}.parquet` |
| Migration Files | `backend/migrations/` |

---

## Next Steps

- See [Data Dictionary](./data-dictionary.md) for detailed field descriptions
- See [Query Patterns](./query-patterns.md) for common query examples
- See [Backup and Restore](./backup-restore.md) for disaster recovery procedures
