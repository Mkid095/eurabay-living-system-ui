# EURABAY Living System v5.0 - API Integration Guide

This document outlines all API endpoints needed for the frontend dashboard to integrate with the Python backend.

## Base URL
```
http://localhost:8000/api
```

## WebSocket URL
```
ws://localhost:8000/ws
```

---

## 1. System Status & Health

### GET /system/status
Returns current system status and health metrics.

**Response:**
```json
{
  "system_version": "v5.0",
  "birth_time": "2024-01-15T10:30:00Z",
  "uptime": "7d 14h 23m",
  "cycles_completed": 1547,
  "is_running": true,
  "mt5_connected": true,
  "health_status": "healthy",
  "cpu_usage": 45.2,
  "memory_usage": 62.8,
  "connection_errors": 0
}
```

### GET /system/health
Returns detailed health monitoring data.

**Response:**
```json
{
  "overall_status": "green",
  "mt5_connection": {
    "status": "connected",
    "last_heartbeat": "2024-01-22T15:30:00Z"
  },
  "data_buffers": {
    "V10": { "ltf": true, "htf": true },
    "V25": { "ltf": true, "htf": true },
    "V50": { "ltf": true, "htf": true },
    "V75": { "ltf": true, "htf": true },
    "V100": { "ltf": true, "htf": true }
  },
  "system_metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "disk_usage": 34.5
  }
}
```

---

## 2. Evolution Metrics

### GET /evolution/metrics
Returns current evolution status and metrics.

**Response:**
```json
{
  "current_generation": 42,
  "controller_decision": "EVOLVE_MODERATE",
  "cycles_completed": 1547,
  "system_version": "v5.0",
  "birth_time": "2024-01-15T10:30:00Z",
  "uptime": "7d 14h 23m"
}
```

### GET /evolution/generation-history
Returns generation progression over time.

**Query Parameters:**
- `days` (optional): Number of days to fetch (default: 7)

**Response:**
```json
[
  {
    "generation": 42,
    "timestamp": "2024-01-22T10:00:00Z",
    "fitness": 74.3,
    "avg_performance": 72.1
  }
]
```

### GET /evolution/controller-history
Returns controller decision history.

**Query Parameters:**
- `limit` (optional): Number of records (default: 20)

**Response:**
```json
[
  {
    "timestamp": "2024-01-22T14:00:00Z",
    "decision": "EVOLVE_MODERATE",
    "performance": 68.5,
    "reason": "Performance dip detected, moderate evolution triggered"
  }
]
```

### GET /evolution/feature-success
Returns success rates of evolved features.

**Response:**
```json
[
  {
    "feature_id": "evolved_momentum",
    "feature_name": "Evolved Momentum",
    "success_rate": 72.5,
    "total_uses": 234,
    "wins": 170,
    "losses": 64,
    "avg_pnl": 12.45
  }
]
```

### GET /evolution/mutation-success
Returns success rates of mutation types.

**Response:**
```json
[
  {
    "mutation_type": "Feature Combination",
    "success_rate": 65.4,
    "total_attempts": 78,
    "successful": 51,
    "avg_fitness_improvement": 8.7
  }
]
```

### GET /evolution/logs
Returns evolution event logs.

**Query Parameters:**
- `limit` (optional): Number of logs (default: 50)
- `type` (optional): Filter by type (MUTATION, EVOLUTION_CYCLE, FEATURE_SUCCESS, FEATURE_FAILURE)

**Response:**
```json
[
  {
    "timestamp": "2024-01-22T14:30:00Z",
    "type": "EVOLUTION_CYCLE",
    "generation": 42,
    "message": "Evolution cycle completed. Fitness improved by 2.1%",
    "details": {
      "fitness_gain": 2.1,
      "mutations_applied": 3
    }
  }
]
```

### POST /evolution/parameters
Update evolution parameters.

**Request Body:**
```json
{
  "mutation_rate": 0.3,
  "adaptive_min_accuracy": 0.55,
  "min_performance_threshold": 0.45,
  "evolution_aggression": 0.5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Evolution parameters updated successfully"
}
```

---

## 3. Market Data

### GET /markets/overview
Returns overview of all Deriv volatility indices.

**Response:**
```json
[
  {
    "symbol": "V10",
    "display_name": "Volatility 10 Index",
    "price": 1234.56,
    "change_24h": 2.3,
    "volume": 15234,
    "spread": 0.5,
    "volatility": 10,
    "trend": "BULLISH"
  }
]
```

### GET /markets/{symbol}/data
Returns market data for specific symbol.

**Path Parameters:**
- `symbol`: V10, V25, V50, V75, V100

**Query Parameters:**
- `timeframe`: M1 or H1
- `bars`: Number of bars (default: 100)

**Response:**
```json
{
  "symbol": "V10",
  "timeframe": "M1",
  "data": [
    {
      "timestamp": "2024-01-22T15:30:00Z",
      "open": 1234.50,
      "high": 1235.20,
      "low": 1233.80,
      "close": 1234.90,
      "volume": 1234
    }
  ]
}
```

### GET /markets/{symbol}/trend
Returns HTF trend analysis for symbol.

**Response:**
```json
{
  "symbol": "V10",
  "trend": "BULLISH",
  "timeframe": "H1",
  "regime": "R_10",
  "confidence": 0.85
}
```

---

## 4. Trading Activity

### GET /trades/active
Returns all active trades with evolution context.

**Response:**
```json
[
  {
    "ticket": "T001234",
    "symbol": "V10",
    "side": "BUY",
    "entry_price": 1234.56,
    "current_price": 1245.32,
    "pnl": 107.60,
    "stop_loss": 1220.45,
    "take_profit": 1260.00,
    "entry_time": "2024-01-22T13:30:00Z",
    "htf_context": "BULLISH H1 R_10",
    "ltf_context": "STRONG_BUY M1",
    "features_used": ["evolved_momentum", "high_vol_chaos"],
    "confidence": 0.87
  }
]
```

### GET /trades/recent
Returns recent closed trades.

**Query Parameters:**
- `limit` (optional): Number of trades (default: 20)

**Response:**
```json
[
  {
    "ticket": "T001233",
    "symbol": "V25",
    "side": "SELL",
    "entry_price": 2345.67,
    "exit_price": 2332.45,
    "pnl": 132.20,
    "entry_time": "2024-01-22T12:00:00Z",
    "exit_time": "2024-01-22T14:30:00Z",
    "outcome": "WIN",
    "htf_context": "BEARISH H1 R_25",
    "ltf_context": "STRONG_SELL M1",
    "features_used": ["trend_reversal"]
  }
]
```

### GET /trades/pending-signals
Returns signals waiting for portfolio approval.

**Response:**
```json
[
  {
    "signal_id": "SIG_001",
    "symbol": "V50",
    "signal_type": "STRONG_BUY",
    "confidence": 0.89,
    "htf_context": "BULLISH H1 R_50",
    "timestamp": "2024-01-22T15:25:00Z",
    "features_used": ["breakout_detector", "regime_adaptive"]
  }
]
```

### GET /trades/execution-log
Returns execution event log.

**Query Parameters:**
- `limit` (optional): Number of logs (default: 50)

**Response:**
```json
[
  {
    "timestamp": "2024-01-22T15:30:00Z",
    "event_type": "EXECUTION",
    "symbol": "V10",
    "action": "BUY",
    "status": "SUCCESS",
    "message": "Trade executed successfully",
    "ticket": "T001234"
  }
]
```

---

## 5. Portfolio & Performance

### GET /portfolio/metrics
Returns portfolio-level metrics.

**Response:**
```json
{
  "total_value": 125000.00,
  "total_pnl": 5234.56,
  "total_pnl_percent": 4.37,
  "active_trades": 5,
  "win_rate": 68.5,
  "current_drawdown": 2.3,
  "max_drawdown": 8.7,
  "total_trades": 234
}
```

### GET /portfolio/equity-history
Returns equity curve data.

**Query Parameters:**
- `days` (optional): Number of days (default: 30)

**Response:**
```json
[
  {
    "timestamp": "2024-01-22T00:00:00Z",
    "equity": 124500.00,
    "balance": 120000.00
  }
]
```

### GET /portfolio/pnl-history
Returns P&L history.

**Query Parameters:**
- `grouping`: daily, weekly, monthly

**Response:**
```json
[
  {
    "period": "2024-01-22",
    "pnl": 523.45,
    "trades": 12,
    "win_rate": 66.7
  }
]
```

### GET /performance/metrics
Returns detailed performance metrics.

**Response:**
```json
{
  "total_trades": 234,
  "winning_trades": 160,
  "losing_trades": 74,
  "win_rate": 68.4,
  "avg_win": 145.23,
  "avg_loss": -78.45,
  "profit_factor": 2.34,
  "sharpe_ratio": 1.87,
  "max_drawdown": 8.7,
  "avg_trade_duration": "2h 15m"
}
```

---

## 6. System Controls

### POST /system/start
Start real-time processing.

**Response:**
```json
{
  "success": true,
  "message": "System started successfully"
}
```

### POST /system/stop
Stop real-time processing.

**Response:**
```json
{
  "success": true,
  "message": "System stopped successfully"
}
```

### POST /system/force-evolution
Manually trigger evolution cycle.

**Response:**
```json
{
  "success": true,
  "message": "Evolution cycle initiated",
  "generation": 43
}
```

### POST /system/override
Enable/disable manual override.

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Manual override enabled"
}
```

---

## 7. Configuration

### GET /config
Get current system configuration.

**Response:**
```json
{
  "symbols": ["V10", "V25", "V50", "V75", "V100"],
  "timeframes": {
    "ltf": "M1",
    "htf": "H1"
  },
  "risk_management": {
    "risk_per_trade": 0.02,
    "max_drawdown": 0.15,
    "max_total_open_trades": 10
  },
  "evolution": {
    "mutation_rate": 0.3,
    "adaptive_min_accuracy": 0.55
  }
}
```

### PUT /config
Update system configuration.

**Request Body:** (same structure as GET response)

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated successfully"
}
```

---

## 8. Logs

### GET /logs/critical-decisions
Get critical decision logs.

**Query Parameters:**
- `limit` (optional): Number of logs (default: 100)
- `component` (optional): Filter by component

**Response:**
```json
[
  {
    "timestamp": "2024-01-22T15:30:00Z",
    "component": "TradingEngine",
    "level": "INFO",
    "message": "Trade executed successfully",
    "details": {}
  }
]
```

### GET /logs/performance
Get performance update logs.

### GET /logs/connection
Get connection health logs.

---

## 9. WebSocket Events

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### Event Types

#### system_status
Real-time system status updates.
```json
{
  "event": "system_status",
  "data": { /* same as GET /system/status */ }
}
```

#### trade_update
Active trade updates.
```json
{
  "event": "trade_update",
  "data": {
    "ticket": "T001234",
    "current_price": 1245.32,
    "pnl": 107.60
  }
}
```

#### new_signal
New trading signal generated.
```json
{
  "event": "new_signal",
  "data": { /* signal object */ }
}
```

#### evolution_event
Evolution system events.
```json
{
  "event": "evolution_event",
  "data": { /* evolution log object */ }
}
```

#### market_update
Real-time market data updates.
```json
{
  "event": "market_update",
  "data": {
    "symbol": "V10",
    "price": 1234.56,
    "timestamp": "2024-01-22T15:30:00Z"
  }
}
```

---

## Implementation Notes

1. **Authentication**: All API endpoints should require authentication. Frontend should include `Authorization: Bearer <token>` header.

2. **Rate Limiting**: Implement rate limiting on backend (e.g., 100 requests per minute per user).

3. **CORS**: Configure CORS to allow frontend origin.

4. **Error Handling**: All endpoints should return consistent error format:
```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

5. **Timestamps**: All timestamps should be in ISO 8601 format (UTC).

6. **WebSocket Reconnection**: Frontend should implement automatic reconnection with exponential backoff.

7. **Data Caching**: Consider implementing caching for frequently accessed data (market overview, configuration).

8. **Pagination**: For endpoints returning large datasets, implement pagination with `page` and `per_page` query parameters.
