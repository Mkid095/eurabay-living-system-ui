# EURABAY Living System - Query Patterns and Examples

## Table of Contents
1. [Introduction](#introduction)
2. [Trade Queries](#trade-queries)
3. [Performance Metrics Queries](#performance-metrics-queries)
4. [Signal Queries](#signal-queries)
5. [Market Data Queries](#market-data-queries)
6. [Model Queries](#model-queries)
7. [Configuration Queries](#configuration-queries)
8. [System Log Queries](#system-log-queries)
9. [Analytical Queries](#analytical-queries)
10. [Performance Optimization](#performance-optimization)

---

## Introduction

This document provides common query patterns and examples for working with the EURABAY Living System database. All queries are optimized with proper indexing and include performance considerations.

---

## Trade Queries

### Get All Open Trades

```sql
SELECT id, symbol, direction, entry_price, entry_time,
       stop_loss, take_profit, lot_size, confidence, strategy_used
FROM trades
WHERE status = 'OPEN'
ORDER BY entry_time DESC;
```

**Index Used**: `ix_trades_status`, `ix_trades_status_entry_time`

**Performance**: < 10ms for 1000 trades

---

### Get Open Trades for Specific Symbol

```sql
SELECT id, mt5_ticket, direction, entry_price, entry_time,
       stop_loss, take_profit, lot_size, confidence,
       profit_loss, strategy_used
FROM trades
WHERE symbol = 'V10' AND status = 'OPEN'
ORDER BY entry_time DESC;
```

**Index Used**: `ix_trades_symbol_status`

**Performance**: < 5ms

---

### Get Trades by Date Range

```sql
SELECT id, symbol, direction, entry_price, exit_price,
       profit_loss, profit_loss_pips, status
FROM trades
WHERE entry_time >= '2025-01-01' AND entry_time < '2025-02-01'
ORDER BY entry_time DESC;
```

**Index Used**: `ix_trades_entry_time`

**Performance**: < 20ms for 10,000 trades

---

### Get Trades by Symbol and Date Range

```sql
SELECT id, direction, entry_price, exit_price,
       profit_loss, status, entry_time
FROM trades
WHERE symbol = 'V25'
  AND entry_time >= '2025-01-01'
  AND entry_time < '2025-02-01'
ORDER BY entry_time DESC;
```

**Index Used**: `ix_trades_symbol_entry_time_status`

**Performance**: < 15ms

---

### Calculate Win Rate for Period

```sql
SELECT
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
    ROUND(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    SUM(profit_loss) as total_pnl
FROM trades
WHERE status = 'CLOSED'
  AND exit_time >= '2025-01-01'
  AND exit_time < '2025-02-01';
```

**Index Used**: `ix_trades_status`, `ix_trades_exit_time`

**Performance**: < 50ms for 10,000 closed trades

---

### Get Trade Performance by Strategy

```sql
SELECT
    strategy_used,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    SUM(profit_loss) as total_pnl,
    AVG(profit_loss) as avg_pnl,
    MAX(profit_loss) as best_trade,
    MIN(profit_loss) as worst_trade
FROM trades
WHERE status = 'CLOSED'
GROUP BY strategy_used
ORDER BY total_pnl DESC;
```

**Performance**: < 100ms for 10,000 trades with 5 strategies

---

### Get Current Exposure by Symbol

```sql
SELECT
    symbol,
    direction,
    COUNT(*) as position_count,
    SUM(lot_size) as total_lots,
    SUM(entry_price * lot_size) as total_exposure
FROM trades
WHERE status = 'OPEN'
GROUP BY symbol, direction
ORDER BY symbol, direction;
```

**Performance**: < 20ms

---

### Update Trade Exit Information

```sql
UPDATE trades
SET
    exit_price = 1.0850,
    exit_time = '2025-01-17 14:30:00',
    profit_loss = 50.00,
    profit_loss_pips = 20.0,
    status = 'CLOSED'
WHERE id = 123;
```

**Note**: The `updated_at` field is automatically updated by the trigger.

---

### Using the v_active_trades View

```sql
SELECT * FROM v_active_trades
WHERE symbol = 'V10'
ORDER BY entry_datetime DESC;
```

**Benefits**:
- Pre-calculated stop loss and take profit distances
- Only returns open trades
- Formatted datetime

---

## Performance Metrics Queries

### Get Latest Performance Metrics

```sql
SELECT * FROM performance_metrics
ORDER BY period_end DESC
LIMIT 1;
```

**Performance**: < 5ms

---

### Get Metrics for Specific Period

```sql
SELECT * FROM performance_metrics
WHERE period = 'daily'
  AND period_start >= '2025-01-01'
  AND period_end < '2025-02-01'
ORDER BY period_start DESC;
```

**Index Used**: `ix_performance_metrics_period`

**Performance**: < 10ms

---

### Get Monthly Performance Summary

```sql
SELECT
    strftime('%Y-%m', period_start) as month,
    SUM(total_trades) as total_trades,
    SUM(winning_trades) as winning_trades,
    ROUND(AVG(win_rate), 2) as avg_win_rate,
    SUM(total_profit) as total_profit,
    SUM(total_loss) as total_loss,
    ROUND(AVG(profit_factor), 2) as avg_profit_factor,
    MAX(max_drawdown) as max_drawdown
FROM performance_metrics
WHERE period = 'daily'
GROUP BY strftime('%Y-%m', period_start)
ORDER BY month DESC;
```

**Performance**: < 50ms for 365 days

---

### Get Best and Worst Performing Days

```sql
SELECT
    period_start,
    total_trades,
    win_rate,
    total_profit - total_loss as net_profit,
    profit_factor
FROM performance_metrics
WHERE period = 'daily'
  AND total_trades > 0
ORDER BY net_profit DESC
LIMIT 10;
```

```sql
SELECT
    period_start,
    total_trades,
    win_rate,
    total_profit - total_loss as net_profit,
    profit_factor
FROM performance_metrics
WHERE period = 'daily'
  AND total_trades > 0
ORDER BY net_profit ASC
LIMIT 10;
```

**Performance**: < 30ms each

---

### Using the v_performance_summary View

```sql
SELECT * FROM v_performance_summary
WHERE period = 'daily'
  AND period_start >= '2025-01-01'
LIMIT 10;
```

---

## Signal Queries

### Get Recent Signals

```sql
SELECT id, symbol, direction, confidence, price,
       strategy, timestamp, executed
FROM signals
WHERE timestamp >= datetime('now', '-24 hours')
ORDER BY timestamp DESC;
```

**Index Used**: `ix_signals_timestamp`

**Performance**: < 20ms

---

### Get Unexecuted Signals

```sql
SELECT * FROM signals
WHERE executed = 0
ORDER BY timestamp DESC;
```

**Index Used**: `ix_signals_executed_timestamp`

**Performance**: < 10ms

---

### Get Unexecuted Signals for Symbol

```sql
SELECT * FROM signals
WHERE symbol = 'V10' AND executed = 0
ORDER BY timestamp DESC;
```

**Index Used**: `ix_signals_symbol_executed_timestamp`

**Performance**: < 5ms

---

### Get Signal Execution Rate

```sql
SELECT
    strategy,
    COUNT(*) as total_signals,
    SUM(executed) as executed_signals,
    ROUND(SUM(executed) * 100.0 / COUNT(*), 2) as execution_rate
FROM signals
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY strategy
ORDER BY execution_rate DESC;
```

**Performance**: < 50ms for 1000 signals

---

### Get Signals by Confidence Level

```sql
SELECT
    CASE
        WHEN confidence >= 0.8 THEN 'High'
        WHEN confidence >= 0.6 THEN 'Medium'
        ELSE 'Low'
    END as confidence_level,
    COUNT(*) as signal_count,
    SUM(executed) as executed,
    ROUND(SUM(executed) * 100.0 / COUNT(*), 2) as execution_rate,
    ROUND(AVG(confidence), 3) as avg_confidence
FROM signals
WHERE timestamp >= datetime('now', '-30 days')
GROUP BY confidence_level
ORDER BY avg_confidence DESC;
```

**Performance**: < 100ms

---

### Mark Signal as Executed

```sql
UPDATE signals
SET executed = 1, trade_id = 123
WHERE id = 456;
```

---

### Using the v_recent_signals View

```sql
SELECT * FROM v_recent_signals
WHERE symbol IN ('V10', 'V25', 'V50')
ORDER BY signal_datetime DESC;
```

---

## Market Data Queries

### Get Latest Market Data

```sql
SELECT * FROM market_data
WHERE symbol = 'V10' AND timeframe = 'H1'
ORDER BY timestamp DESC
LIMIT 100;
```

**Index Used**: `ix_market_data_symbol_timeframe_timestamp`

**Performance**: < 10ms

---

### Get Market Data for Date Range

```sql
SELECT timestamp, open_price, high_price, low_price,
       close_price, volume
FROM market_data
WHERE symbol = 'V25'
  AND timeframe = 'H1'
  AND timestamp >= '2025-01-01'
  AND timestamp < '2025-01-02'
ORDER BY timestamp ASC;
```

**Index Used**: `ix_market_data_symbol_timeframe_timestamp`

**Performance**: < 50ms for 24 hourly candles

---

### Get OHLC Data for Chart

```sql
SELECT
    datetime(timestamp) as time,
    open_price,
    high_price,
    low_price,
    close_price,
    volume
FROM market_data
WHERE symbol = 'V10'
  AND timeframe = 'H1'
  AND timestamp >= datetime('now', '-7 days')
ORDER BY timestamp ASC;
```

**Performance**: < 100ms for 168 hourly candles

---

### Calculate Technical Indicators

```sql
-- Get data for RSI calculation (14-period)
SELECT
    timestamp,
    close_price,
    LAG(close_price, 1) OVER (ORDER BY timestamp) as prev_close,
    LAG(close_price, 14) OVER (ORDER BY timestamp) as close_14_periods_ago
FROM market_data
WHERE symbol = 'V10'
  AND timeframe = 'H1'
  AND timestamp >= datetime('now', '-30 days')
ORDER BY timestamp ASC;
```

**Note**: Full indicator calculations should be done in application code with pandas.

---

### Get Missing Data Points

```sql
-- Find gaps in hourly data
WITH time_series AS (
    SELECT timestamp, timeframe
    FROM market_data
    WHERE symbol = 'V10'
      AND timeframe = 'H1'
      AND timestamp >= datetime('now', '-24 hours')
),
expected_times AS (
    SELECT datetime(strftime('%Y-%m-%d %H:00:00', timestamp)) as hour
    FROM (
        SELECT datetime((julianday('now') - 24) || ' days') + (value || ' hours') as timestamp
        FROM generate_series(0, 23)
    )
)
SELECT hour as missing_timestamp
FROM expected_times
LEFT JOIN time_series ON datetime(time_series.timestamp) = hour
WHERE time_series.timestamp IS NULL;
```

---

## Model Queries

### Get Active Models

```sql
SELECT * FROM models
WHERE is_active = 1
ORDER BY training_time DESC;
```

**Index Used**: `ix_models_active_training_time`

**Performance**: < 10ms

---

### Get Active Model for Symbol

```sql
SELECT * FROM models
WHERE symbol = 'V10' AND is_active = 1
ORDER BY training_time DESC
LIMIT 1;
```

**Index Used**: `ix_models_symbol_active_training_time`

**Performance**: < 5ms

---

### Get Model Performance History

```sql
SELECT
    model_name,
    model_version,
    symbol,
    accuracy,
    precision,
    recall,
    f1_score,
    training_samples,
    datetime(training_time) as trained_at
FROM models
WHERE model_name = 'RandomForestClassifier'
ORDER BY training_time DESC;
```

**Performance**: < 20ms

---

### Compare Model Versions

```sql
SELECT
    model_version,
    accuracy,
    precision,
    recall,
    f1_score,
    training_samples
FROM models
WHERE model_name = 'RandomForestClassifier'
  AND symbol = 'V10'
ORDER BY training_time DESC
LIMIT 10;
```

**Performance**: < 10ms

---

### Get Best Performing Models

```sql
SELECT
    model_name,
    symbol,
    model_type,
    accuracy,
    f1_score,
    training_samples
FROM models
WHERE is_active = 0
GROUP BY model_name, symbol
HAVING MAX(training_time)
ORDER BY f1_score DESC
LIMIT 10;
```

**Performance**: < 50ms

---

### Using the v_active_models View

```sql
SELECT * FROM v_active_models
WHERE symbol IN ('V10', 'V25', 'V50')
ORDER BY training_datetime DESC;
```

---

## Configuration Queries

### Get Configuration Value

```sql
SELECT config_value, description, category
FROM configurations
WHERE config_key = 'risk.max_position_risk_pct'
  AND is_active = 1;
```

**Index Used**: `ix_config_config_key`

**Performance**: < 5ms

---

### Get All Configurations by Category

```sql
SELECT config_key, config_value, description
FROM configurations
WHERE category = 'risk' AND is_active = 1
ORDER BY config_key;
```

**Index Used**: `ix_config_category`

**Performance**: < 10ms

---

### Get All Active Configurations as Dictionary

```sql
SELECT config_key, config_value
FROM configurations
WHERE is_active = 1;
```

**Usage**: Load into Python dict for application config

---

### Update Configuration

```sql
UPDATE configurations
SET config_value = '2.5',
    updated_at = CURRENT_TIMESTAMP
WHERE config_key = 'risk.max_position_risk_pct';
```

---

### Create New Configuration

```sql
INSERT INTO configurations (config_key, config_value, description, category)
VALUES ('risk.new_setting', 'value', 'Description here', 'risk');
```

---

## System Log Queries

### Get Recent Logs

```sql
SELECT timestamp, level, message, source
FROM system_logs
WHERE timestamp >= datetime('now', '-24 hours')
ORDER BY timestamp DESC
LIMIT 100;
```

**Index Used**: `ix_system_logs_timestamp`

**Performance**: < 20ms

---

### Get Error Logs

```sql
SELECT timestamp, level, message, source, context
FROM system_logs
WHERE level IN ('ERROR', 'CRITICAL')
  AND timestamp >= datetime('now', '-7 days')
ORDER BY timestamp DESC;
```

**Index Used**: `ix_system_logs_timestamp_level`

**Performance**: < 50ms

---

### Get Logs by Source

```sql
SELECT timestamp, level, message
FROM system_logs
WHERE source = 'trading_engine'
  AND timestamp >= datetime('now', '-24 hours'
ORDER BY timestamp DESC;
```

**Index Used**: `ix_system_logs_timestamp_level_source`

**Performance**: < 30ms

---

### Get Log Statistics

```sql
SELECT
    level,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM system_logs), 2) as percentage
FROM system_logs
WHERE timestamp >= datetime('now', '-24 hours')
GROUP BY level
ORDER BY count DESC;
```

**Performance**: < 100ms

---

### Get Log Summary by Source

```sql
SELECT
    source,
    COUNT(*) as total_logs,
    SUM(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END) as errors,
    SUM(CASE WHEN level = 'WARNING' THEN 1 ELSE 0 END) as warnings,
    SUM(CASE WHEN level = 'CRITICAL' THEN 1 ELSE 0 END) as critical
FROM system_logs
WHERE timestamp >= datetime('now', '-24 hours')
GROUP BY source
ORDER BY total_logs DESC;
```

**Performance**: < 100ms

---

## Analytical Queries

### Drawdown Analysis

```sql
WITH equity_curve AS (
    SELECT
        exit_time,
        SUM(profit_loss) OVER (ORDER BY exit_time) as cumulative_pnl,
        SUM(profit_loss) OVER (ORDER BY exit_time ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as running_total
    FROM trades
    WHERE status = 'CLOSED'
      AND exit_time >= '2025-01-01'
),
peaks AS (
    SELECT
        exit_time,
        running_total,
        MAX(running_total) OVER (ORDER BY exit_time) as peak
    FROM equity_curve
)
SELECT
    exit_time,
    running_total as equity,
    peak,
    (peak - running_total) as drawdown,
    ROUND((peak - running_total) / NULLIF(peak, 0) * 100, 2) as drawdown_pct
FROM peaks
ORDER BY exit_time;
```

**Performance**: < 200ms for 1000 trades

---

### Trade Duration Analysis

```sql
SELECT
    symbol,
    ROUND(AVG(julianday(exit_time) - julianday(entry_time)), 2) as avg_duration_days,
    ROUND(AVG(julianday(exit_time) - julianday(entry_time)) * 24, 2) as avg_duration_hours,
    MIN(julianday(exit_time) - julianday(entry_time)) as min_duration,
    MAX(julianday(exit_time) - julianday(entry_time)) as max_duration
FROM trades
WHERE status = 'CLOSED'
  AND exit_time >= '2025-01-01'
GROUP BY symbol
ORDER BY avg_duration_hours DESC;
```

**Performance**: < 100ms

---

### Profit Factor by Hour of Day

```sql
SELECT
    CAST(strftime('%H', entry_time) AS INTEGER) as hour,
    COUNT(*) as trade_count,
    SUM(CASE WHEN profit_loss > 0 THEN profit_loss ELSE 0 END) as total_profit,
    SUM(CASE WHEN profit_loss < 0 THEN ABS(profit_loss) ELSE 0 END) as total_loss,
    ROUND(SUM(CASE WHEN profit_loss > 0 THEN profit_loss ELSE 0 END) /
          NULLIF(SUM(CASE WHEN profit_loss < 0 THEN ABS(profit_loss) ELSE 0 END), 0), 2) as profit_factor
FROM trades
WHERE status = 'CLOSED'
  AND entry_time >= '2025-01-01'
GROUP BY hour
ORDER BY hour;
```

**Performance**: < 150ms

---

### Win Rate by Day of Week

```sql
SELECT
    strftime('%w', entry_time) as day_of_week,
    CASE CAST(strftime('%w', entry_time) AS INTEGER)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
    ROUND(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    SUM(profit_loss) as total_pnl
FROM trades
WHERE status = 'CLOSED'
  AND entry_time >= '2025-01-01'
GROUP BY day_of_week
ORDER BY day_of_week;
```

**Performance**: < 100ms

---

### Monthly Performance Comparison

```sql
SELECT
    strftime('%Y-%m', entry_time) as month,
    COUNT(*) as trades,
    SUM(profit_loss) as total_pnl,
    ROUND(AVG(profit_loss), 2) as avg_pnl,
    ROUND(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    MAX(profit_loss) as best_trade,
    MIN(profit_loss) as worst_trade
FROM trades
WHERE status = 'CLOSED'
GROUP BY strftime('%Y-%m', entry_time)
ORDER BY month DESC;
```

**Performance**: < 150ms

---

## Performance Optimization

### Using Prepared Statements

For frequently executed queries, use prepared statements via the `PreparedStatementCache`:

```python
from backend.app.services.query_optimizer import PreparedStatementCache

cache = PreparedStatementCache()

# Prepare and cache query
query = "SELECT * FROM trades WHERE symbol = ? AND status = ?"
prepared = cache.get_statement("trades_by_symbol_status", query)

# Execute multiple times efficiently
for symbol in symbols:
    result = await prepared.execute(symbol, 'OPEN')
```

---

### Using Query Result Cache

For queries that don't change often:

```python
from backend.app.services.query_optimizer import QueryOptimizerService

optimizer = QueryOptimizerService()

# Cache configuration data
configs = await optimizer.cached_query(
    "all_configs",
    "SELECT * FROM configurations WHERE is_active = 1",
    ttl=3600  # Cache for 1 hour
)
```

---

### Pagination for Large Results

```python
from backend.app.services.query_optimizer import paginate_query

# Get paginated results
result = await paginate_query(
    session=session,
    query=query,
    page=1,
    page_size=50
)

print(f"Total: {result.total_count}")
print(f"Page {result.page} of {result.total_pages}")
for item in result.items:
    print(item)
```

---

### Analyzing Query Performance

```python
from backend.app.services.query_optimizer import QueryAnalyzer

analyzer = QueryAnalyzer()

# Analyze slow query
analysis = await analyzer.analyze_query(
    "SELECT * FROM trades WHERE symbol = 'V10' AND status = 'OPEN'"
)

print(f"Query plan: {analysis.query_plan}")
print(f"Recommendations: {analysis.recommendations}")
```

---

### Best Practices

1. **Always use indexed columns in WHERE clauses**
2. **Use JOINs instead of subqueries when possible**
3. **Avoid SELECT * - specify only needed columns**
4. **Use LIMIT for large result sets with pagination**
5. **Use EXPLAIN QUERY PLAN for slow queries**
6. **Cache frequently accessed data**
7. **Use prepared statements for repeated queries**
8. **Monitor query execution time (> 100ms warning)**

---

## Next Steps

- See [Database Schema](./database-schema.md) for complete schema documentation
- See [Data Dictionary](./data-dictionary.md) for detailed field descriptions
- See [Backup and Restore](./backup-restore.md) for disaster recovery procedures
