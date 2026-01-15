# PRD: MetaTrader 5 Integration (Hybrid with Deriv.com)

## Overview

The EURABAY Living System v5.0 implements a **hybrid trading architecture** that combines:
- **Deriv.com** as the liquidity provider for volatility indices (V10, V25, V50, V75, V100)
- **MetaTrader 5 (MT5)** as the trading execution platform, analysis engine, and data storage system

This PRD documents the complete MT5 integration that enables order execution, technical analysis, position management, and data persistence within the unified system.

## Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EURABAY Living System v5.0                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐          │
│  │   Deriv.com API  │              │  MetaTrader 5    │          │
│  │  (Liquidity)     │◄────────────►│  (Execution)     │          │
│  │                  │  Price Feed  │                  │          │
│  │  - V10, V25...   │              │  - Order Mgmt    │          │
│  │  - Real-time     │              │  - Analysis      │          │
│  │  - Synthetic     │              │  - Indicators    │          │
│  └──────────────────┘              │  - History       │          │
│                                   └──────────────────┘          │
│                                           │                      │
│                                           ▼                      │
│                              ┌─────────────────────┐             │
│                              │  Python Backend     │             │
│                              │  (Orchestration)    │             │
│                              └─────────────────────┘             │
│                                           │                      │
│                                           ▼                      │
│                              ┌─────────────────────┐             │
│                              │  Frontend Dashboard │             │
│                              │  (Next.js UI)        │             │
│                              └─────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Goals

- Establish and maintain MT5 terminal connection
- Execute orders through MT5 platform
- Use MT5 indicators for technical analysis
- Store all trading data in MT5 history
- Retrieve account information from MT5
- Synchronize Deriv price data with MT5
- Monitor MT5 connection health
- Handle MT5 errors and reconnection

## Current State

**Problem:**
- MT5 connection status shown in UI but not implemented
- No MT5 order execution logic
- Missing MT5 account information display
- No MT5 indicator analysis integration
- MT5 trade history not utilized
- No MT5 error handling
- Missing MT5 terminal management

**Impact:**
- Cannot execute actual trades
- Missing technical analysis from MT5
- No trade history persistence
- System appears functional but cannot trade

## User Stories

### US-001: Implement MT5 Terminal Connection Management

**Description:** As a system, I need to establish and monitor MT5 terminal connection.

**Acceptance Criteria:**
- [ ] Create `src/lib/mt5.ts` with MT5 client class
- [ ] Implement `connectMT5()` function with terminal path/config
- [ ] Implement connection health check (ping every 30s)
- [ ] Display MT5 connection status in header (connected/disconnected/error)
- [ ] Show MT5 terminal info (account number, company, server)
- [ ] Implement auto-reconnect on disconnect
- [ ] Log all connection state changes
- [ ] Handle MT5 terminal not found error
- [ ] Handle MT5 login failure
- [ ] Display connection quality indicator (latency, last heartbeat)
- [ ] Typecheck passes
- [ ] Verify MT5 connects successfully

**Priority:** 1

**Technical Implementation:**

```typescript
// src/lib/mt5.ts
export interface MT5ConnectionInfo {
  connected: boolean;
  accountNumber?: number;
  company?: string;
  server?: string;
  terminalPath?: string;
  lastHeartbeat?: string;
  latency?: number;
}

export interface MT5AccountInfo {
  login: number;
  company: string;
  currency: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  leverage: number;
}

class MT5Client {
  private connected = false;
  private reconnectAttempts = 0;
  private pingInterval: NodeJS.Timeout | null = null;

  async connect(config: MT5Config): Promise<MT5ConnectionInfo>
  async disconnect(): Promise<void>
  async isConnected(): Promise<boolean>
  async getAccountInfo(): Promise<MT5AccountInfo>
  async healthCheck(): Promise<boolean>
}

export const mt5Client = new MT5Client();
```

### US-002: Display MT5 Account Information

**Description:** As a trader, I need to see my MT5 account details.

**Acceptance Criteria:**
- [ ] Create `MT5AccountInfo.tsx` component
- [ ] Display account number
- [ ] Display account currency
- [ ] Display current balance
- [ ] Display current equity
- [ ] Display used margin
- [ ] Display free margin
- [ ] Display margin level percentage
- [ ] Display leverage
- [ ] Display account company/broker
- [ ] Show equity growth chart (last 30 days)
- [ ] Auto-refresh every 5 seconds
- [ ] Typecheck passes
- [ ] Verify account info displays correctly

**Priority:** 1

**Technical Implementation:**

```typescript
// src/components/dashboard/MT5AccountInfo.tsx
export function MT5AccountInfo() {
  const { accountInfo, loading, error } = useMT5AccountInfo();

  if (loading) return <AccountInfoSkeleton />;
  if (error) return <ErrorState error={error} />;
  if (!accountInfo) return <div>Not connected to MT5</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account Information</CardTitle>
        <div className="text-sm text-muted-foreground">
          Account: {accountInfo.login} @ {accountInfo.company}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label="Balance" value={`${accountInfo.balance.toFixed(2)} ${accountInfo.currency}`} />
          <MetricCard label="Equity" value={`${accountInfo.equity.toFixed(2)} ${accountInfo.currency}`} />
          <MetricCard label="Used Margin" value={`${accountInfo.margin.toFixed(2)} ${accountInfo.currency}`} />
          <MetricCard label="Free Margin" value={`${accountInfo.freeMargin.toFixed(2)} ${accountInfo.currency}`} />
          <MetricCard label="Margin Level" value={`${accountInfo.marginLevel.toFixed(2)}%`} />
          <MetricCard label="Leverage" value={`1:${accountInfo.leverage}`} />
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-003: Implement MT5 Order Execution

**Description:** As a system, I need to execute trades through MT5 terminal.

**Acceptance Criteria:**
- [ ] Create `executeMT5Order()` function
- [ ] Support market orders (instant execution)
- [ ] Support pending orders (limit, stop)
- [ ] Calculate lot size based on risk percentage
- [ ] Set stop loss and take profit levels
- [ ] Add trade comment with evolution generation
- [ ] Add magic number for system identification
- [ ] Handle order rejection errors
- [ ] Handle not enough money error
- [ ] Handle market closed error
- [ ] Return order ticket on success
- [ ] Log all order attempts
- [ ] Typecheck passes
- [ ] Verify orders execute in MT5

**Priority:** 2

**Technical Implementation:**

```typescript
// src/lib/mt5/orders.ts
export interface MT5OrderRequest {
  symbol: string;  // V10, V25, V50, V75, V100
  orderType: 'MARKET' | 'LIMIT' | 'STOP';
  direction: 'BUY' | 'SELL';
  lots: number;
  price?: number;  // For pending orders
  stopLoss?: number;
  takeProfit?: number;
  comment?: string;
  magicNumber?: number;
}

export interface MT5OrderResult {
  success: boolean;
  ticket?: number;
  error?: string;
  executionPrice?: number;
}

export async function executeMT5Order(request: MT5OrderRequest): Promise<MT5OrderResult> {
  try {
    const response = await apiClient.post<MT5OrderResult>('/mt5/orders/execute', {
      symbol: request.symbol,
      order_type: request.orderType,
      trade_direction: request.direction,
      volume: request.lots,
      price: request.price,
      sl: request.stopLoss,
      tp: request.takeProfit,
      comment: request.comment || `EURABAY Gen ${getCurrentGeneration()}`,
      magic: request.magicNumber || 123456,  // System magic number
    });

    return response.data;
  } catch (error) {
    console.error('MT5 Order execution failed:', error);
    return { success: false, error: error.message };
  }
}
```

### US-004: Implement MT5 Position Management

**Description:** As a trader, I need to manage open positions in MT5.

**Acceptance Criteria:**
- [ ] Create `getMT5Positions()` function to get all open positions
- [ ] Display MT5 position ID alongside system ticket
- [ ] Implement `closeMT5Position()` function
- [ ] Implement `modifyMT5Position()` for SL/TP changes
- [ ] Support partial position close
- [ ] Show position profit/loss in real-time
- [ ] Show position open time and duration
- [ ] Show position comment (evolution generation)
- [ ] Handle position close errors
- [ ] Log all position modifications
- [ ] Typecheck passes
- [ ] Verify positions sync correctly

**Priority:** 2

**Technical Implementation:**

```typescript
// src/lib/mt5/positions.ts
export interface MT5Position {
  ticket: number;
  symbol: string;
  direction: 'BUY' | 'SELL';
  lots: number;
  openPrice: number;
  currentPrice: number;
  stopLoss?: number;
  takeProfit?: number;
  openTime: string;
  profit: number;
  swap: number;
  comment: string;
  magicNumber: number;
}

export async function getMT5Positions(): Promise<MT5Position[]> {
  const response = await apiClient.get<MT5Position[]>('/mt5/positions/open');
  return response.data;
}

export async function closeMT5Position(ticket: number, lots?: number): Promise<boolean> {
  const response = await apiClient.post<boolean>('/mt5/positions/close', {
    ticket,
    volume: lots,  // If undefined, close entire position
  });
  return response.data;
}

export async function modifyMT5Position(
  ticket: number,
  stopLoss?: number,
  takeProfit?: number
): Promise<boolean> {
  const response = await apiClient.put<boolean>('/mt5/positions/modify', {
    ticket,
    sl: stopLoss,
    tp: takeProfit,
  });
  return response.data;
}
```

### US-005: Integrate MT5 Technical Indicators

**Description:** As a system, I need to use MT5 indicators for market analysis.

**Acceptance Criteria:**
- [ ] Create `src/lib/mt5/indicators.ts` with indicator functions
- [ ] Implement `getRSI()` function for Relative Strength Index
- [ ] Implement `getMACD()` function for trend analysis
- [ ] Implement `getMovingAverage()` for trend following
- [ ] Implement `getBollingerBands()` for volatility
- [ ] Implement `getATR()` for volatility measurement
- [ ] Support multiple timeframes (M1, M5, M15, M30, H1, H4, D1)
- [ ] Cache indicator values for performance
- [ ] Return indicator values for evolution features
- [ ] Typecheck passes
- [ ] Verify indicators return correct values

**Priority:** 3

**Technical Implementation:**

```typescript
// src/lib/mt5/indicators.ts
export interface IndicatorRequest {
  symbol: string;
  timeframe: string;  // M1, M5, M15, M30, H1, H4, D1
  period: number;
}

export interface IndicatorResult {
  symbol: string;
  timeframe: string;
  values: number[];
  lastValue: number;
  timestamp: string;
}

// Get Relative Strength Index
export async function getRSI(request: IndicatorRequest): Promise<IndicatorResult> {
  const response = await apiClient.post<IndicatorResult>('/mt5/indicators/rsi', request);
  return response.data;
}

// Get MACD (Moving Average Convergence Divergence)
export async function getMACD(request: IndicatorRequest): Promise<{
  macd: IndicatorResult;
  signal: IndicatorResult;
  histogram: IndicatorResult;
}> {
  const response = await apiClient.post('/mt5/indicators/macd', request);
  return response.data;
}

// Get Simple/Exponential Moving Average
export async function getMovingAverage(request: IndicatorRequest & {
  maType: 'SMA' | 'EMA';
}): Promise<IndicatorResult> {
  const response = await apiClient.post<IndicatorResult>('/mt5/indicators/ma', request);
  return response.data;
}

// Get Bollinger Bands
export async function getBollingerBands(request: IndicatorRequest): Promise<{
  upper: IndicatorResult;
  middle: IndicatorResult;
  lower: IndicatorResult;
}> {
  const response = await apiClient.post('/mt5/indicators/bollinger', request);
  return response.data;
}

// Get Average True Range
export async function getATR(request: IndicatorRequest): Promise<IndicatorResult> {
  const response = await apiClient.post<IndicatorResult>('/mt5/indicators/atr', request);
  return response.data;
}
```

### US-006: Retrieve MT5 Trade History

**Description:** As a trader, I need to access my complete MT5 trade history.

**Acceptance Criteria:**
- [ ] Create `getMT5TradeHistory()` function
- [ ] Support date range filtering
- [ ] Support symbol filtering
- [ ] Retrieve closed orders
- [ ] Retrieve deal history
- [ ] Display MT5 order ticket
- [ ] Display order open/close times
- [ ] Display order profit/loss
- [ ] Display order commission
- [ ] Display order swap
- [ ] Display order comment
- [ ] Export trade history to CSV
- [ ] Typecheck passes
- [ ] Verify history displays correctly

**Priority:** 3

**Technical Implementation:**

```typescript
// src/lib/mt5/history.ts
export interface MT5TradeHistory {
  ticket: number;
  symbol: string;
  direction: 'BUY' | 'SELL';
  lots: number;
  openPrice: number;
  closePrice: number;
  openTime: string;
  closeTime: string;
  profit: number;
  commission: number;
  swap: number;
  comment: string;
  magicNumber: number;
}

export async function getMT5TradeHistory(params: {
  startDate?: string;
  endDate?: string;
  symbol?: string;
}): Promise<MT5TradeHistory[]> {
  const response = await apiClient.get<MT5TradeHistory[]>('/mt5/history/trades', {
    params,
  });
  return response.data;
}

export async function exportMT5HistoryToCSV(trades: MT5TradeHistory[]): Promise<void> {
  const csv = convertToCSV(trades);
  downloadFile(csv, `mt5_trades_${Date.now()}.csv`);
}
```

### US-007: Synchronize Deriv Data with MT5

**Description:** As a system, I need to sync Deriv price data with MT5 for analysis.

**Acceptance Criteria:**
- [ ] Implement `syncDerivToMT5()` function
- [ ] Push Deriv V10 price to MT5 V10 symbol
- [ ] Push Deriv V25 price to MT5 V25 symbol
- [ ] Push Deriv V50 price to MT5 V50 symbol
- [ ] Push Deriv V75 price to MT5 V75 symbol
- [ ] Push Deriv V100 price to MT5 V100 symbol
- [ ] Update MT5 charts with live Deriv prices
- [ ] Handle price sync failures
- [ ] Log price sync attempts
- [ ] Sync every 1 second during market hours
- [ ] Typecheck passes
- [ ] Verify prices sync correctly

**Priority:** 4

**Technical Implementation:**

```typescript
// src/lib/mt5/sync.ts
export interface DerivPriceData {
  symbol: string;
  price: number;
  timestamp: string;
}

export async function syncDerivToMT5(prices: DerivPriceData[]): Promise<void> {
  try {
    await apiClient.post('/mt5/sync/prices', {
      prices: prices.map(p => ({
        symbol: p.symbol,
        bid: p.price,
        ask: p.price,
        timestamp: p.timestamp,
      })),
    });
    console.log('Successfully synced Deriv prices to MT5');
  } catch (error) {
    console.error('Failed to sync Deriv prices to MT5:', error);
  }
}

// In a component or hook:
useEffect(() => {
  const syncInterval = setInterval(async () => {
    const derivPrices = await fetchDerivMarketOverview();
    await syncDerivToMT5(derivPrices);
  }, 1000);  // Sync every second

  return () => clearInterval(syncInterval);
}, []);
```

### US-008: Handle MT5 Errors and Reconnection

**Description:** As a system, I need to handle MT5 errors and auto-reconnect.

**Acceptance Criteria:**
- [ ] Implement MT5 error handler
- [ ] Detect MT5 terminal disconnect
- [ ] Implement exponential backoff reconnection
- [ ] Show user-friendly error messages
- [ ] Log all MT5 errors with details
- [ ] Attempt to reconnect up to 5 times
- [ ] Disable trading when MT5 disconnected
- [ ] Show reconnection progress
- [ ] Send notification when reconnected
- [ ] Track reconnection success rate
- [ ] Typecheck passes
- [ ] Verify error handling works

**Priority:** 4

**Technical Implementation:**

```typescript
// src/lib/mt5/errors.ts
export enum MT5ErrorCode {
  TERMINAL_NOT_FOUND = 'TERMINAL_NOT_FOUND',
  LOGIN_FAILED = 'LOGIN_FAILED',
  CONNECTION_LOST = 'CONNECTION_LOST',
  ORDER_REJECTED = 'ORDER_REJECTED',
  NOT_ENOUGH_MONEY = 'NOT_ENOUGH_MONEY',
  MARKET_CLOSED = 'MARKET_CLOSED',
  INVALID_PRICE = 'INVALID_PRICE',
}

export interface MT5Error {
  code: MT5ErrorCode;
  message: string;
  details?: any;
}

export function handleMT5Error(error: MT5Error): void {
  console.error('MT5 Error:', error);

  switch (error.code) {
    case MT5ErrorCode.CONNECTION_LOST:
      showToast('MT5 connection lost. Attempting to reconnect...', 'warning');
      attemptMT5Reconnect();
      break;

    case MT5ErrorCode.ORDER_REJECTED:
      showToast(`Order rejected: ${error.message}`, 'error');
      break;

    case MT5ErrorCode.NOT_ENOUGH_MONEY:
      showToast('Insufficient funds to open position', 'error');
      break;

    case MT5ErrorCode.MARKET_CLOSED:
      showToast('Market is currently closed', 'warning');
      break;

    default:
      showToast(`MT5 Error: ${error.message}`, 'error');
  }
}

export async function attemptMT5Reconnect(): Promise<boolean> {
  for (let i = 0; i < 5; i++) {
    try {
      await delay(Math.pow(2, i) * 1000);  // Exponential backoff
      const connected = await mt5Client.connect();
      if (connected) {
        showToast('Reconnected to MT5', 'success');
        return true;
      }
    } catch (error) {
      console.error(`Reconnection attempt ${i + 1} failed`, error);
    }
  }

  showToast('Failed to reconnect to MT5 after 5 attempts', 'error');
  return false;
}
```

### US-009: Display MT5 Terminal Status

**Description:** As an admin, I need detailed MT5 terminal status information.

**Acceptance Criteria:**
- [ ] Create `MT5TerminalStatus.tsx` component
- [ ] Display MT5 terminal path
- [ ] Display MT5 build version
- [ ] Display MT5 connection status
- [ ] Display MT5 ping latency
- [ ] Display last heartbeat time
- [ ] Display data buffers status for each symbol
- [ ] Display trade allowed flag
- [ ] Display trade context info
- [ ] Add "Restart MT5 Connection" button
- [ ] Add "Test MT5 Connection" button
- [ ] Show MT5 error log
- [ ] Auto-refresh every 5 seconds
- [ ] Typecheck passes
- [ ] Verify status displays correctly

**Priority:** 5

**Technical Implementation:**

```typescript
// src/components/dashboard/MT5TerminalStatus.tsx
export function MT5TerminalStatus() {
  const { terminalStatus, loading } = useMT5TerminalStatus();

  return (
    <Card>
      <CardHeader>
        <CardTitle>MT5 Terminal Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Status</Label>
              <Badge className={terminalStatus.connected ? 'bg-green-500' : 'bg-red-500'}>
                {terminalStatus.connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            <div>
              <Label>Latency</Label>
              <div>{terminalStatus.latency}ms</div>
            </div>
            <div>
              <Label>Build</Label>
              <div>{terminalStatus.build}</div>
            </div>
            <div>
              <Label>Last Heartbeat</Label>
              <div>{new Date(terminalStatus.lastHeartbeat).toLocaleString()}</div>
            </div>
          </div>

          <div>
            <Label>Data Buffers</Label>
            <Table>
              <TableBody>
                {Object.entries(terminalStatus.dataBuffers).map(([symbol, buffer]) => (
                  <TableRow key={symbol}>
                    <TableCell>{symbol}</TableCell>
                    <TableCell>LTF: {buffer.ltf ? '✓' : '✗'}</TableCell>
                    <TableCell>HTF: {buffer.htf ? '✓' : '✗'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex gap-2">
            <Button onClick={testConnection}>Test Connection</Button>
            <Button onClick={restartConnection} variant="outline">
              Restart Connection
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-010: Implement MT5 Trade Signal Integration

**Description:** As a system, I need to execute trades based on signals through MT5.

**Acceptance Criteria:**
- [ ] Create `executeSignalThroughMT5()` function
- [ ] Receive signal from evolution system
- [ ] Validate signal (direction, confidence, features)
- [ ] Calculate position size based on risk parameters
- [ ] Set SL/TP based on volatility (ATR)
- [ ] Execute market order through MT5
- [ ] Store signal ID in MT5 order comment
- [ ] Return MT5 ticket to system
- [ ] Link system ticket to MT5 ticket
- [ ] Handle execution failures
- [ ] Log all signal executions
- [ ] Typecheck passes
- [ ] Verify signals execute correctly

**Priority:** 5

**Technical Implementation:**

```typescript
// src/lib/mt5/signals.ts
export interface TradingSignal {
  signalId: string;
  symbol: string;
  direction: 'BUY' | 'SELL';
  confidence: number;
  features: string[];
  stopLoss?: number;
  takeProfit?: number;
  riskPercent: number;
}

export interface ExecutedTrade {
  systemTicket: string;
  mt5Ticket: number;
  symbol: string;
  direction: 'BUY' | 'SELL';
  lots: number;
  entryPrice: number;
  stopLoss?: number;
  takeProfit?: number;
  executionTime: string;
}

export async function executeSignalThroughMT5(
  signal: TradingSignal,
  accountInfo: MT5AccountInfo
): Promise<ExecutedTrade> {
  // Calculate position size based on risk
  const riskAmount = accountInfo.equity * (signal.riskPercent / 100);
  const atr = await getATR({ symbol: signal.symbol, timeframe: 'H1', period: 14 });
  const stopLossDistance = atr.lastValue * 2;  // 2x ATR for SL
  const lotSize = calculateLotSize(riskAmount, stopLossDistance, signal.symbol);

  // Execute order through MT5
  const result = await executeMT5Order({
    symbol: signal.symbol,
    orderType: 'MARKET',
    direction: signal.direction,
    lots: lotSize,
    stopLoss: signal.stopLoss,
    takeProfit: signal.takeProfit,
    comment: `Signal: ${signal.signalId} | Gen: ${getCurrentGeneration()} | Features: ${signal.features.join(',')}`,
  });

  if (!result.success || !result.ticket) {
    throw new Error(`Failed to execute signal: ${result.error}`);
  }

  return {
    systemTicket: signal.signalId,
    mt5Ticket: result.ticket,
    symbol: signal.symbol,
    direction: signal.direction,
    lots: lotSize,
    entryPrice: result.executionPrice || 0,
    stopLoss: signal.stopLoss,
    takeProfit: signal.takeProfit,
    executionTime: new Date().toISOString(),
  };
}
```

## Functional Requirements

- FR-1: MT5 connection must be established before any trading operations
- FR-2: All orders must be executed through MT5 terminal
- FR-3: MT5 account info must sync every 5 seconds
- FR-4: Deriv price data must sync to MT5 every 1 second
- FR-5: MT5 indicators must be accessible for evolution features
- FR-6: All trade history must be stored in MT5
- FR-7: MT5 connection errors must trigger auto-reconnect
- FR-8: MT5 terminal status must be visible to admin users
- FR-9: System tickets must link to MT5 order tickets
- FR-10: MT5 position updates must reflect in system within 500ms

## Non-Goals

- No MT5 Expert Advisor (EA) development
- No custom MT5 indicator development
- No MT5 market depth (Level 2) data
- No MT5 strategy tester integration
- No multiple MT5 account support in this phase

## Technical Considerations

### MT5 API Integration Points

The system integrates with MT5 through a Python backend that:

1. **Connects to MT5 Terminal** using MetaTrader5 Python library
2. **Executes orders** via MT5 order API
3. **Retrieves data** via MT5 API calls
4. **Synchronizes prices** from Deriv to MT5 custom symbols

### Required API Endpoints

#### MT5 Connection Management
- `POST /mt5/connect` - Connect to MT5 terminal
- `POST /mt5/disconnect` - Disconnect from MT5
- `GET /mt5/status` - Get connection status
- `GET /mt5/terminal-info` - Get terminal information

#### MT5 Account Data
- `GET /mt5/account-info` - Get account information
- `GET /mt5/account-balance` - Get current balance
- `GET /mt5/account-equity` - Get current equity

#### MT5 Order Execution
- `POST /mt5/orders/execute` - Execute market/pending order
- `GET /mt5/orders/{ticket}` - Get order details
- `GET /mt5/orders/open` - Get all open orders

#### MT5 Position Management
- `GET /mt5/positions/open` - Get all open positions
- `POST /mt5/positions/close` - Close position
- `PUT /mt5/positions/modify` - Modify position SL/TP

#### MT5 Indicators
- `POST /mt5/indicators/rsi` - Get RSI values
- `POST /mt5/indicators/macd` - Get MACD values
- `POST /mt5/indicators/ma` - Get Moving Average values
- `POST /mt5/indicators/bollinger` - Get Bollinger Bands
- `POST /mt5/indicators/atr` - Get ATR values

#### MT5 History
- `GET /mt5/history/trades` - Get trade history
- `GET /mt5/history/orders` - Get order history
- `GET /mt5/history/deals` - Get deal history

#### MT5 Data Sync
- `POST /mt5/sync/prices` - Sync Deriv prices to MT5
- `POST /mt5/sync/symbols` - Sync symbol definitions

### WebSocket Events for MT5

- `mt5_connected` - MT5 connection established
- `mt5_disconnected` - MT5 connection lost
- `mt5_order_opened` - New order opened in MT5
- `mt5_order_closed` - Order closed in MT5
- `mt5_position_modified` - Position SL/TP modified
- `mt5_price_update` - Price updated in MT5
- `mt5_error` - MT5 error occurred

### Dependencies
- Python backend with MetaTrader5 library
- MT5 terminal installed and running
- Valid MT5 account with trading enabled
- Custom symbols configured in MT5 for V10-V100

### Performance Requirements
- MT5 connection establishment: < 5 seconds
- Order execution time: < 1 second
- Price sync latency: < 500ms
- Position update latency: < 500ms
- Indicator calculation: < 2 seconds

### Error Handling Strategy
- Terminal not found: Show setup instructions
- Login failed: Show credentials error, allow retry
- Connection lost: Auto-reconnect with exponential backoff
- Order rejected: Show specific error reason
- Not enough money: Show required margin vs available
- Market closed: Disable trading, show market hours

## Success Metrics

- MT5 connection uptime > 99%
- Order execution success rate > 98%
- Price sync accuracy = 100%
- Position sync latency < 500ms
- Auto-reconnect success rate > 95%
- Zero lost orders in MT5 history

## Implementation Order

1. US-001: Implement MT5 Terminal Connection Management
2. US-002: Display MT5 Account Information
3. US-003: Implement MT5 Order Execution
4. US-004: Implement MT5 Position Management
5. US-007: Synchronize Deriv Data with MT5
6. US-005: Integrate MT5 Technical Indicators
7. US-008: Handle MT5 Errors and Reconnection
8. US-010: Implement MT5 Trade Signal Integration
9. US-006: Retrieve MT5 Trade History
10. US-009: Display MT5 Terminal Status

## Testing Strategy

### Unit Tests
- Test MT5 connection logic
- Test order execution parameters
- Test position modification logic
- Test error handling for all MT5 errors
- Test indicator data parsing

### Integration Tests
- Test order execution flow
- Test position sync from MT5
- Test price sync to MT5
- Test reconnection logic
- Test signal execution through MT5

### Manual Testing
- Verify MT5 connects successfully
- Test order execution in live MT5
- Verify positions sync correctly
- Test all error scenarios
- Verify price sync accuracy
- Test indicator calculations

### MT5-Specific Testing
- Test with demo account first
- Test order execution with 0.01 lots
- Test SL/TP modification
- Test partial position close
- Test during market open/close
- Test with high volatility

## Known Issues & Risks

- MT5 terminal must be running and logged in
- MT5 Python library requires Windows
- Custom symbols (V10-V100) must be configured in MT5
- Price sync may have small delays
- MT5 may reject orders during high volatility
- Reconnection may lose pending orders
- Indicator calculations may differ between platforms

## Related PRDs

- PRD: Backend API Integration (MT5 endpoints)
- PRD: WebSocket Integration (MT5 events)
- PRD: Trading System Features (MT5 order execution)
- PRD: Market Data Features (Deriv price sync)
- PRD: Evolution System Features (MT5 indicator usage)
