# PRD: WebSocket Integration

## Overview

The EURABAY Living System requires real-time data updates for trading activity, evolution events, market data, and system status. This PRD implements WebSocket integration to replace the current 3-second polling with true push-based real-time updates.

## Goals

- Implement WebSocket connection management with auto-reconnect
- Receive real-time updates for all trading activity
- Receive real-time evolution events
- Receive real-time market data updates
- Receive real-time system status updates
- Handle connection failures gracefully
- Maintain connection state across page refreshes
- Optimize bandwidth with targeted subscriptions

## Current State

**Problem:**
- No WebSocket connection exists
- Dashboard polls API every 3-5 seconds (inefficient)
- No real-time updates for trade execution
- No real-time evolution event notifications
- No real-time market price updates
- Stale data between polling intervals

**Impact:**
- Delayed visibility into trading activity (up to 5 seconds)
- Missed evolution events between polls
- Unnecessary server load from constant polling
- Poor user experience for time-sensitive trading data

## User Stories

### US-001: Create WebSocket Client Foundation

**Description:** As a developer, I need a WebSocket client with connection management.

**Acceptance Criteria:**
- [ ] Create `src/lib/websocket.ts` with WebSocket client class
- [ ] Implement connection state management (connecting, connected, disconnected, error)
- [ ] Implement auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- [ ] Implement connection timeout (10 seconds)
- [ ] Implement manual disconnect and reconnect methods
- [ ] Add connection health checks (ping/pong every 30s)
- [ ] Log all connection state changes
- [ ] Handle WebSocket close events with appropriate reconnect logic
- [ ] Add connection attempt counter for monitoring
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```typescript
// src/lib/websocket.ts
type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

class WSClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;

  connect(): void
  disconnect(): void
  reconnect(): void
  getState(): ConnectionState
  on(event: string, handler: Function): void
  emit(event: string, data: any): void
}

export const wsClient = new WSClient();
```

### US-002: Add WebSocket Authentication

**Description:** As a system, I need to authenticate WebSocket connections.

**Acceptance Criteria:**
- [ ] Add authentication token to WebSocket connection URL
- [ ] Implement token refresh logic for long-lived connections
- [ ] Handle authentication failure responses
- [ ] Disconnect and show error if authentication fails
- [ ] Store auth token securely for reconnection
- [ ] Clear auth token on logout
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```typescript
// src/lib/websocket.ts
class WSClient {
  private getAuthToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  connect(): void {
    const token = this.getAuthToken();
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}?token=${token}`;
    this.ws = new WebSocket(wsUrl);
  }
}
```

### US-003: Create WebSocket Event System

**Description:** As a developer, I need an event system to handle WebSocket messages.

**Acceptance Criteria:**
- [ ] Create `src/lib/websocket/events.ts` with event type definitions
- [ ] Define TypeScript interfaces for all WebSocket event types
- [ ] Create event handler registration system
- [ ] Create event dispatcher to route messages to handlers
- [ ] Add event validation with Zod schemas
- [ ] Add event logging in development mode
- [ ] Handle malformed event messages gracefully
- [ ] Typecheck passes

**Priority:** 2

**Technical Implementation:**

```typescript
// src/lib/websocket/events.ts
export enum WSEventType {
  SYSTEM_STATUS = 'system_status',
  TRADE_UPDATE = 'trade_update',
  NEW_SIGNAL = 'new_signal',
  EVOLUTION_EVENT = 'evolution_event',
  MARKET_UPDATE = 'market_update',
  PERFORMANCE_UPDATE = 'performance_update',
}

export interface WSEvent<T = any> {
  event: WSEventType;
  data: T;
  timestamp: string;
  correlationId?: string;
}

export interface TradeUpdateEvent {
  ticket: string;
  currentPrice: number;
  pnl: number;
  status: 'active' | 'closed';
}

// Similar interfaces for all event types
```

### US-004: Implement Trade Update Events

**Description:** As a user, I need to see real-time updates to my active trades.

**Acceptance Criteria:**
- [ ] Subscribe to `trade_update` events on WebSocket connection
- [ ] Update active trades in real-time when prices change
- [ ] Update P&L values instantly
- [ ] Add visual indicators for updated values (flash animation)
- [ ] Move trades to recent trades when closed
- [ ] Show toast notification for large P&L changes (>10%)
- [ ] Update portfolio metrics in real-time based on trade updates
- [ ] Typecheck passes
- [ ] Verify in browser that trades update in real-time

**Priority:** 3

**Technical Implementation:**

```typescript
// src/hooks/useRealTimeTrades.ts
export function useRealTimeTrades() {
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    const handleTradeUpdate = (event: WSEvent<TradeUpdateEvent>) => {
      setTrades(prev => prev.map(trade =>
        trade.ticket === event.data.ticket
          ? { ...trade, ...event.data }
          : trade
      ));
    };

    wsClient.on('trade_update', handleTradeUpdate);
    return () => wsClient.off('trade_update', handleTradeUpdate);
  }, []);

  return trades;
}
```

### US-005: Implement Evolution Event Notifications

**Description:** As a user, I need to see real-time evolution events as they happen.

**Acceptance Criteria:**
- [ ] Subscribe to `evolution_event` events on WebSocket connection
- [ ] Append new evolution events to evolution log viewer
- [ ] Update generation metrics when new generation starts
- [ ] Update controller decision when it changes
- [ ] Show toast notification for important evolution events (new generation, aggressive evolution)
- [ ] Auto-scroll evolution log to show newest events
- [ ] Add visual indicator for new events (badge count)
- [ ] Typecheck passes
- [ ] Verify in browser that evolution events display in real-time

**Priority:** 3

**Technical Implementation:**

```typescript
// src/hooks/useRealTimeEvolution.ts
export function useRealTimeEvolution() {
  const [events, setEvents] = useState<EvolutionLog[]>([]);
  const [metrics, setMetrics] = useState<EvolutionMetrics | null>(null);

  useEffect(() => {
    const handleEvolutionEvent = (event: WSEvent<EvolutionLog>) => {
      setEvents(prev => [event.data, ...prev]);

      // Update metrics if it's a generation change
      if (event.data.type === 'EVOLUTION_CYCLE') {
        setMetrics(prev => prev ? {
          ...prev,
          currentGeneration: event.data.generation,
        } : null);
      }
    };

    wsClient.on('evolution_event', handleEvolutionEvent);
    return () => wsClient.off('evolution_event', handleEvolutionEvent);
  }, []);

  return { events, metrics };
}
```

### US-006: Implement Market Data Updates

**Description:** As a user, I need to see real-time market price updates.

**Acceptance Criteria:**
- [ ] Subscribe to `market_update` events on WebSocket connection
- [ ] Update market overview prices in real-time
- [ ] Add visual indicators for price changes (green/red flash)
- [ ] Update price change percentages
- [ ] Highlight markets with significant price movements (>2%)
- [ ] Update market trend indicators when they change
- [ ] Typecheck passes
- [ ] Verify in browser that market prices update in real-time

**Priority:** 3

**Technical Implementation:**

```typescript
// src/hooks/useRealTimeMarkets.ts
export function useRealTimeMarkets() {
  const [markets, setMarkets] = useState<MarketOverview[]>([]);

  useEffect(() => {
    const handleMarketUpdate = (event: WSEvent<MarketUpdate>) => {
      setMarkets(prev => prev.map(market =>
        market.symbol === event.data.symbol
          ? { ...market, ...event.data, lastUpdate: Date.now() }
          : market
      ));
    };

    wsClient.on('market_update', handleMarketUpdate);
    return () => wsClient.off('market_update', handleMarketUpdate);
  }, []);

  return markets;
}
```

### US-007: Implement System Status Monitoring

**Description:** As a user, I need to see real-time system status updates.

**Acceptance Criteria:**
- [ ] Subscribe to `system_status` events on WebSocket connection
- [ ] Update system status indicator in real-time
- [ ] Show alert banner when system status changes to unhealthy
- [ ] Update CPU/memory usage indicators
- [ ] Show connection error when WebSocket disconnects
- [ ] Display reconnection attempts
- [ ] Update uptime counter in real-time
- [ ] Typecheck passes
- [ ] Verify in browser that system status updates correctly

**Priority:** 4

**Technical Implementation:**

```typescript
// src/hooks/useRealTimeSystemStatus.ts
export function useRealTimeSystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');

  useEffect(() => {
    const handleSystemStatus = (event: WSEvent<SystemStatus>) => {
      setStatus(event.data);
    };

    const handleConnectionChange = (state: ConnectionState) => {
      setConnectionState(state);
    };

    wsClient.on('system_status', handleSystemStatus);
    wsClient.on('connection_change', handleConnectionChange);

    return () => {
      wsClient.off('system_status', handleSystemStatus);
      wsClient.off('connection_change', handleConnectionChange);
    };
  }, []);

  return { status, connectionState };
}
```

### US-008: Add Connection Status Indicator

**Description:** As a user, I need to know if the real-time connection is working.

**Acceptance Criteria:**
- [ ] Create connection status indicator component in header
- [ ] Show green dot for connected
- [ ] Show yellow dot for connecting
- [ ] Show red dot for disconnected/error
- [ ] Show tooltip with connection details (latency, reconnect attempts)
- [ ] Add "Reconnect" button when disconnected
- [ ] Add connection quality indicator (good/degraded/poor based on latency)
- [ ] Typecheck passes
- [ ] Verify in browser that connection indicator displays correctly

**Priority:** 4

**Technical Implementation:**

```typescript
// src/components/dashboard/ConnectionStatus.tsx
export function ConnectionStatus() {
  const { state, latency, reconnectAttempts } = useConnectionState();

  const statusConfig = {
    connected: { color: 'bg-green-500', text: 'Connected' },
    connecting: { color: 'bg-yellow-500', text: 'Connecting...' },
    disconnected: { color: 'bg-red-500', text: 'Disconnected' },
    error: { color: 'bg-red-500', text: 'Connection Error' },
  };

  const config = statusConfig[state];

  return (
    <div className="flex items-center gap-2">
      <div className={`h-2 w-2 rounded-full ${config.color} animate-pulse`} />
      <span className="text-sm">{config.text}</span>
      {latency && <span className="text-xs text-muted-foreground">{latency}ms</span>}
    </div>
  );
}
```

### US-009: Implement Subscription Management

**Description:** As a system, I need to manage which data streams to subscribe to.

**Acceptance Criteria:**
- [ ] Create subscription manager in WebSocket client
- [ ] Implement subscribe/unsubscribe methods for each data type
- [ ] Only subscribe to data for visible dashboard tabs
- [ ] Unsubscribe from hidden tabs to save bandwidth
- [ ] Subscribe to all data when on dashboard view
- [ ] Implement subscription acknowledgment from server
- [ ] Log all subscription changes
- [ ] Typecheck passes

**Priority:** 5

**Technical Implementation:**

```typescript
// src/lib/websocket/subscriptions.ts
export enum SubscriptionType {
  TRADES = 'trades',
  EVOLUTION = 'evolution',
  MARKETS = 'markets',
  SYSTEM_STATUS = 'system_status',
  PERFORMANCE = 'performance',
}

class SubscriptionManager {
  private subscriptions = new Set<SubscriptionType>();

  subscribe(type: SubscriptionType): void {
    if (!this.subscriptions.has(type)) {
      wsClient.emit('subscribe', { type });
      this.subscriptions.add(type);
    }
  }

  unsubscribe(type: SubscriptionType): void {
    if (this.subscriptions.has(type)) {
      wsClient.emit('unsubscribe', { type });
      this.subscriptions.delete(type);
    }
  }

  unsubscribeAll(): void {
    this.subscriptions.forEach(type => this.unsubscribe(type));
  }
}

export const subscriptionManager = new SubscriptionManager();
```

### US-010: Add WebSocket Error Recovery

**Description:** As a user, I need the system to recover from connection errors automatically.

**Acceptance Criteria:**
- [ ] Detect WebSocket connection drops
- [ ] Attempt to reconnect with exponential backoff
- [ ] Show "Reconnecting..." message to user
- [ ] Restore all subscriptions after reconnect
- [ ] Request full data refresh after reconnect
- [ ] Show error message after 3 failed reconnect attempts
- [ ] Add "Manual Reconnect" button after failed auto-reconnect
- [ ] Log all reconnection attempts
- [ ] Typecheck passes
- [ ] Verify in browser that reconnection works correctly

**Priority:** 5

**Technical Implementation:**

```typescript
// src/lib/websocket/recovery.ts
class WSRecovery {
  private maxReconnectAttempts = 3;
  private reconnectDelay = [1000, 2000, 4000, 8000, 30000];

  async reconnect(): Promise<boolean> {
    for (let i = 0; i < this.maxReconnectAttempts; i++) {
      try {
        await this.delay(this.reconnectDelay[i]);
        await wsClient.connect();
        return true;
      } catch (error) {
        console.error(`Reconnect attempt ${i + 1} failed`, error);
      }
    }
    return false;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

## Functional Requirements

- FR-1: WebSocket must connect within 2 seconds of page load
- FR-2: WebSocket must auto-reconnect after connection loss
- FR-3: WebSocket must use exponential backoff for reconnection attempts
- FR-4: Trade updates must be received within 500ms of backend event
- FR-5: Evolution events must be received within 500ms of backend event
- FR-6: Market updates must be received within 500ms of backend event
- FR-7: Connection status must be visible to user at all times
- FR-8: WebSocket must send ping every 30 seconds to maintain connection
- FR-9: WebSocket must handle pong responses to verify connection health
- FR-10: Subscriptions must be restored after reconnection

## Non-Goals

- No binary data protocols (MsgPack, Protobuf) - use JSON
- No peer-to-peer WebRTC connections
- No message queuing for offline scenarios
- No WebSocket compression negotiation
- No alternative transport fallback (Server-Sent Events, long polling)

## Technical Considerations

### Dependencies
- Native WebSocket API (browser)
- No external WebSocket library needed

### Browser Compatibility
- WebSocket API supported in all modern browsers
- Fallback to polling for older browsers (if needed)

### Performance Requirements
- Initial connection must establish in under 2 seconds
- Message propagation delay must be under 500ms
- Reconnection must complete within 10 seconds
- Memory footprint must remain under 10MB for message queue

### Bandwidth Optimization
- Subscribe only to data for active tab
- Unsubscribe from hidden tabs
- Batch multiple updates into single message when possible
- Use delta updates for large data structures

### Error Handling
- Handle invalid WebSocket URLs gracefully
- Handle server shutdown (close code 1001)
- Handle network interruptions
- Handle malformed messages
- Handle rate limiting from server

### Security
- Use WSS (WebSocket Secure) in production
- Include authentication token in connection URL
- Validate all incoming messages
- Sanitize all data before rendering

## Success Metrics

- WebSocket connection success rate > 99%
- Average message latency < 500ms
- Reconnection success rate > 95%
- Zero message loss during reconnection
- Connection uptime > 99.9%
- Subscriptions restored 100% after reconnection
- User-visible connection status updates within 1 second

## Implementation Order

1. US-001: Create WebSocket Client Foundation
2. US-002: Add WebSocket Authentication
3. US-003: Create WebSocket Event System
4. US-008: Add Connection Status Indicator
5. US-009: Implement Subscription Management
6. US-010: Add WebSocket Error Recovery
7. US-004: Implement Trade Update Events
8. US-005: Implement Evolution Event Notifications
9. US-006: Implement Market Data Updates
10. US-007: Implement System Status Monitoring

## Testing Strategy

### Unit Tests
- Test WebSocket client connection logic
- Test reconnection logic with various failure scenarios
- Test event handler registration and cleanup
- Test subscription management
- Test message parsing and validation

### Integration Tests
- Test end-to-end connection flow
- Test message handling in components
- Test state updates from WebSocket events
- Test reconnection with data restoration

### Manual Testing
- Test connection with backend running
- Test reconnection by stopping/starting backend
- Test slow network conditions (Chrome DevTools)
- Test connection with invalid auth token
- Test message handling with malformed data
- Verify all real-time updates in browser

### Load Testing
- Test with 100+ concurrent WebSocket connections
- Test message throughput with high-frequency updates
- Test memory usage over extended connection period

## Known Issues & Risks

- Backend WebSocket server not yet implemented
- CORS policies may block WebSocket connections
- Proxy servers may timeout long-lived connections
- Mobile browsers may throttle WebSocket in background
- Authentication token expiration during long-lived connections

## Related PRDs

- PRD: Backend API Integration (HTTP endpoints)
- PRD: Authentication & User Management (auth tokens)
- PRD: Trading System Features (trade events)
- PRD: Evolution System Features (evolution events)
- PRD: Market Data Features (market events)
