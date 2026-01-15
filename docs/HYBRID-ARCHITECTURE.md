# EURABAY Living System v5.0 - Hybrid Architecture Integration

## Executive Summary

The EURABAY Living System implements a **unique hybrid trading architecture** that combines:
1. **Deriv.com** - Synthetic volatility indices market data provider
2. **MetaTrader 5 (MT5)** - Professional trading execution platform
3. **Custom Evolution Engine** - Genetic algorithm for strategy optimization

This document explains how all components integrate and why this hybrid approach is critical.

---

## Why This Hybrid Architecture?

### Deriv.com Provides:
- ✅ **Synthetic Markets** - V10, V25, V50, V75, V100 volatility indices
- ✅ **24/7 Trading** - Always available, no market hours
- ✅ **Consistent Volatility** - Predictable volatility patterns
- ✅ **API Access** - Real-time price feeds

### MetaTrader 5 Provides:
- ✅ **Professional Execution** - Institutional-grade order routing
- ✅ **Advanced Indicators** - 50+ built-in technical indicators
- ✅ **Robust Backtesting** - Strategy optimization capabilities
- ✅ **Trade History** - Comprehensive data storage
- ✅ **Position Management** - Advanced order types and risk management

### Evolution Engine Provides:
- ✅ **Adaptive Strategies** - Automatically evolves trading rules
- ✅ **Feature Selection** - Identifies most profitable indicators
- ✅ **Parameter Optimization** - Fine-tunes strategy parameters
- ✅ **Complete Transparency** - Every evolution decision is logged

---

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EURABAY Living System v5.0                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Frontend Dashboard                             │  │
│  │                     (Next.js 15 + React 19)                           │  │
│  │  - Real-time UI updates                                              │  │
│  │  - Trade management                                                   │  │
│  │  - Evolution monitoring                                               │  │
│  │  - System controls                                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       WebSocket Real-time Layer                       │  │
│  │  - Trade updates                                                      │  │
│  │  - Evolution events                                                   │  │
│  │  - MT5 connection status                                              │  │
│  │  - Market price updates                                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Python Backend Layer                           │  │
│  │                   (FastAPI/Flask Application)                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │  │
│  │  │   Trading    │  │  Evolution   │  │    Data      │               │  │
│  │  │   Engine     │  │    Engine    │  │  Processor   │               │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                  ┌─────────────────────┴─────────────────────┐               │
│                  │                                           │               │
│                  ▼                                           ▼               │
│  ┌───────────────────────┐                    ┌───────────────────────┐     │
│  │     Deriv.com API     │                    │    MetaTrader 5       │     │
│  │  (Market Data Source) │                    │  (Execution Platform) │     │
│  │                       │◄──────────────────►│                       │     │
│  │  - V10-V100 Prices    │   Price Sync        │  - Order Execution    │     │
│  │  - Real-time Quotes   │                    │  - Position Mgmt      │     │
│  │  - Synthetic Data     │                    │  - Technical Ind.     │     │
│  │  - 24/7 Availability  │                    │  - Trade History      │     │
│  └───────────────────────┘                    └───────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Trade Execution Example

### 1. Signal Generation
```
Evolution Engine (Python)
  ↓
Analyzes MT5 indicators (RSI, MACD, MA, etc.)
  ↓
Generates trading signal with confidence score
  ↓
Sends signal to pending queue
  ↓
Frontend displays signal in "Pending Signals" component
```

### 2. Signal Approval
```
Trader approves signal (Frontend UI)
  ↓
API call to POST /trades/signals/{id}/approve
  ↓
Backend validates and processes approval
  ↓
Calculates position size based on risk %
  ↓
Determines SL/TP using ATR from MT5
  ↓
Sends order execution command to MT5
```

### 3. Order Execution (MT5)
```
Backend: executeMT5Order(request)
  ↓
MT5 Terminal receives order command
  ↓
MT5 executes order on V10 symbol (custom symbol synced from Deriv)
  ↓
MT5 returns order ticket #12345
  ↓
Backend stores system_ticket + mt5_ticket mapping
  ↓
WebSocket event: mt5_order_opened
  ↓
Frontend updates "Active Trades" table
```

### 4. Real-Time Monitoring
```
Deriv API: V10 price updates every second
  ↓
Backend: syncDerivToMT5() - pushes price to MT5
  ↓
MT5: Updates position P&L in real-time
  ↓
Backend: getMT5Positions() - fetches updated positions
  ↓
WebSocket event: trade_update
  ↓
Frontend: Updates P&L in "Active Trades" table
```

---

## Key Integration Points

### 1. Deriv.com ↔ MT5 Price Sync

**Why?** MT5 doesn't natively support Deriv volatility indices.

**How?**
- Python backend fetches Deriv prices via API every 1 second
- Backend pushes prices to MT5 custom symbols (V10, V25, V50, V75, V100)
- MT5 maintains charts and history for these custom symbols
- Evolution engine analyzes MT5 charts for signal generation

**API Endpoints:**
```
GET /markets/overview (Deriv)
  ↓
POST /mt5/sync/prices (MT5)
```

### 2. MT5 Indicators → Evolution Features

**Why?** Leverage MT5's professional-grade indicators.

**How?**
- Evolution engine calls MT5 indicator APIs
- Retrieves RSI, MACD, Moving Averages, Bollinger Bands, ATR
- Uses indicator values as features for genetic algorithm
- Evolves optimal combinations of indicators

**API Endpoints:**
```
POST /mt5/indicators/rsi
POST /mt5/indicators/macd
POST /mt5/indicators/ma
POST /mt5/indicators/bollinger
POST /mt5/indicators/atr
```

### 3. System Ticket ↔ MT5 Ticket Mapping

**Why?** Track trades across both systems.

**How?**
- System generates internal ticket ID (e.g., SIG-2024-001)
- MT5 returns MT5 ticket number (e.g., 12345)
- Backend stores mapping in database
- Frontend displays both IDs for traceability

**Database Schema:**
```sql
CREATE TABLE trades (
  system_ticket VARCHAR(50) PRIMARY KEY,
  mt5_ticket INT UNIQUE NOT NULL,
  symbol VARCHAR(10),
  direction ENUM('BUY', 'SELL'),
  lots DECIMAL(10,2),
  entry_price DECIMAL(10,2),
  sl DECIMAL(10,2),
  tp DECIMAL(10,2),
  open_time TIMESTAMP,
  evolution_gen INT,
  features_used JSON,
  FOREIGN KEY (mt5_ticket) REFERENCES mt5_history(ticket)
);
```

### 4. MT5 Trade History → System Analytics

**Why?** MT5 provides authoritative trade history storage.

**How?**
- All trades executed through MT5 stored in MT5 history
- Backend fetches history via MT5 API
- Populates system analytics and performance charts
- Enables comprehensive trade analysis

**API Endpoints:**
```
GET /mt5/history/trades
  ↓
Processed into analytics
  ↓
Displayed in frontend charts
```

---

## Critical Success Factors

### 1. MT5 Connection Stability
- MT5 terminal must remain running and logged in
- Python backend must maintain persistent connection
- Auto-reconnect with exponential backoff
- Health checks every 30 seconds

### 2. Price Synchronization
- Deriv prices must sync to MT5 within 500ms
- No price gaps during sync failures
- Fallback mechanism if sync fails

### 3. Order Execution Speed
- Signal approval to MT5 execution: < 2 seconds
- Order confirmation to frontend: < 500ms
- Position updates: < 1 second

### 4. Indicator Accuracy
- MT5 indicator calculations must be precise
- Same parameters across all timeframes
- Consistent with MT5 terminal values

---

## Error Scenarios & Handling

### Scenario 1: MT5 Disconnect
```
Detection: WebSocket event mt5_disconnected
  ↓
Frontend: Show red "Disconnected" badge
  ↓
Backend: Attempt auto-reconnect (5 attempts, exponential backoff)
  ↓
If successful: WebSocket event mt5_connected
  ↓
If failed: Disable trading, show error message
```

### Scenario 2: Deriv API Failure
```
Detection: Price sync fails
  ↓
Backend: Log error, use last known price
  ↓
MT5: Continue with last price (no new bars)
  ↓
Evolution: Pause signal generation
  ↓
Frontend: Show "Market Data Unavailable" warning
```

### Scenario 3: Order Rejection
```
MT5: Rejects order (insufficient margin, market closed, etc.)
  ↓
Backend: Capture MT5 error code
  ↓
WebSocket event: mt5_error
  ↓
Frontend: Show specific error message to user
  ↓
System: Log rejection, do not retry automatically
```

### Scenario 4: Indicator Calculation Failure
```
Backend: MT5 indicator API fails
  ↓
Evolution: Use fallback indicators or pause
  ↓
Frontend: Show "Indicators Unavailable"
  ↓
System: Log error, continue with available data
```

---

## Configuration Requirements

### MT5 Terminal Setup
```ini
[MT5 Configuration]
Terminal Path = C:\Program Files\MetaTrader 5\terminal64.exe
Account Number = 12345678
Server = MetaQuotes-Demo
Login = Automated
Password = ********

[Custom Symbols]
V10 = Volatility 10 Index
V25 = Volatility 25 Index
V50 = Volatility 50 Index
V75 = Volatility 75 Index
V100 = Volatility 100 Index
```

### Deriv API Setup
```env
DERIV_APP_ID = 1089
DERIV_API_URL = wss://ws.binaryws.com/websockets/v3?app_id=1089
DERIV_SYMBOLS = VOL10,VOL25,VOL50,VOL75,VOL100
```

### System Configuration
```env
PYTHON_BACKEND_URL = http://localhost:8000
WEBSOCKET_URL = ws://localhost:8000/ws
PRICE_SYNC_INTERVAL = 1000  # 1 second
INDICATOR_CACHE_TTL = 5000   # 5 seconds
```

---

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| MT5 Connection Uptime | > 99% | Continuous monitoring |
| Price Sync Latency | < 500ms | Deriv → MT5 |
| Order Execution Time | < 2s | Approval → MT5 ticket |
| Position Update Latency | < 1s | MT5 → Frontend |
| Indicator Calculation | < 2s | MT5 API response |
| WebSocket Message Latency | < 100ms | Backend → Frontend |
| Evolution Cycle Time | < 30s | Full generation |

---

## Testing Strategy

### Unit Tests
- MT5 connection logic
- Price sync algorithm
- Order execution parameters
- Indicator data parsing
- Error handling for all scenarios

### Integration Tests
- End-to-end trade execution
- Price sync accuracy
- Position synchronization
- WebSocket event propagation
- Reconnection logic

### Manual Tests
- Connect to MT5 demo account
- Execute test trades with 0.01 lots
- Verify price sync accuracy
- Test all error scenarios
- Validate indicator values

### Load Tests
- 100 concurrent signals
- 10 simultaneous open positions
- High-frequency price updates (100/second)
- 24-hour continuous operation

---

## Rollout Plan

### Phase 1: Infrastructure Setup (Week 1)
- Install MT5 terminal
- Configure custom symbols (V10-V100)
- Set up Python backend
- Establish Deriv API connection

### Phase 2: Core Integration (Weeks 2-3)
- Implement MT5 connection management
- Implement price sync Deriv → MT5
- Implement order execution through MT5
- Implement position synchronization

### Phase 3: Evolution Integration (Week 4)
- Connect MT5 indicators to evolution engine
- Implement feature extraction from indicators
- Test evolution cycles with MT5 data

### Phase 4: Frontend Integration (Weeks 5-6)
- Display MT5 connection status
- Show MT5 account information
- Display MT5 ticket numbers
- Real-time position updates

### Phase 5: Testing & Optimization (Weeks 7-8)
- End-to-end testing
- Performance optimization
- Error handling refinement
- Documentation

### Phase 6: Production Deployment (Week 9)
- Deploy to production
- Monitor for 48 hours
- Fix any issues
- Full rollout

---

## Monitoring & Alerting

### Key Metrics to Monitor
- MT5 connection status
- Price sync success rate
- Order execution success rate
- Position synchronization accuracy
- Indicator response times
- Evolution cycle completion rate

### Alert Triggers
- MT5 disconnected > 1 minute
- Price sync failure > 5 consecutive attempts
- Order rejection rate > 10%
- Position sync gap > 10 seconds
- Indicator API failure rate > 5%

---

## FAQs

**Q: Why not trade directly on Deriv?**
A: MT5 provides professional-grade execution, advanced order types, comprehensive backtesting, and robust trade history storage that Deriv's API doesn't offer.

**Q: Why not use MT5 for everything?**
A: MT5 doesn't natively support Deriv's synthetic volatility indices. The hybrid approach gives us the best of both platforms.

**Q: What happens if MT5 crashes?**
A: The system detects disconnection, attempts auto-reconnect, and disables trading until reconnection is successful.

**Q: Can I use any MT5 broker?**
A: Yes, but the broker must support custom symbols for the V10-V100 volatility indices.

**Q: How are prices synced between Deriv and MT5?**
A: Python backend fetches Deriv prices every second and pushes them to MT5 custom symbols via MT5 API.

**Q: What happens to open trades if the system restarts?**
A: MT5 maintains all open positions. On restart, the system fetches open positions from MT5 and resumes monitoring.

---

## Conclusion

The EURABAY Living System's hybrid architecture is not just a technical choice—it's a strategic advantage:

1. **Deriv.com** provides unique synthetic markets not available elsewhere
2. **MT5** provides institutional-grade execution and analysis
3. **Evolution Engine** provides adaptive strategy optimization

Together, they create a trading system that is:
- ✅ More reliable than either platform alone
- ✅ More feature-rich than single-platform solutions
- ✅ More adaptable with evolutionary optimization
- ✅ More transparent with complete audit trails

This architecture is what makes the EURABAY Living System truly unique in the algorithmic trading space.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-14
**Author:** EURABAY Development Team
