# PRD: Trading System Features

## Overview

The EURABAY Living System is an algorithmic trading platform for Deriv.com volatility indices. This PRD implements the complete trading functionality including active trades monitoring, signal management, trade execution, and trade history.

## Goals

- Display real-time active trades with evolution context
- Show pending signals awaiting portfolio approval
- Display recent trade history with outcomes
- Show trade execution logs in real-time
- Allow manual trade approval/rejection
- Display trade performance metrics
- Show HTF/LTF context for each trade
- Track which evolved features contributed to each trade

## Current State

**Problem:**
- `EnhancedActiveTradesTable` exists but uses mock data
- `PendingSignals` exists but uses mock data
- `RecentTrades` exists but uses mock data
- `ExecutionLog` exists but uses mock data
- No actual connection to trading backend
- No manual approval/rejection functionality
- No filtering or search capabilities
- Missing trade detail views

**Impact:**
- Users cannot see actual trading activity
- Cannot approve/reject signals
- No visibility into trade execution
- Missing critical trading information
- System appears functional but trades nothing

## User Stories

### US-001: Update Active Trades Table with Real Data

**Description:** As a trader, I need to see all my active trades with real-time updates.

**Acceptance Criteria:**
- [ ] Update `EnhancedActiveTradesTable.tsx` to use real API data
- [ ] Display ticket ID, symbol, side (BUY/SELL)
- [ ] Display entry price, current price, P&L
- [ ] Display stop loss and take profit levels
- [ ] Display entry time and duration
- [ ] Display HTF context (e.g., "BULLISH H1 R_10")
- [ ] Display LTF context (e.g., "STRONG_BUY M1")
- [ ] Display evolved features used (as badges)
- [ ] Display confidence score (as progress bar)
- [ ] Color-code P&L (green for profit, red for loss)
- [ ] Add visual flash effect when price updates
- [ ] Add trade detail view on row click
- [ ] Add auto-refresh every 3 seconds
- [ ] Typecheck passes
- [ ] Verify in browser that active trades display correctly

**Priority:** 1

**Technical Implementation:**

```typescript
// src/components/dashboard/EnhancedActiveTradesTable.tsx
interface ActiveTrade {
  ticket: string;
  symbol: 'V10' | 'V25' | 'V50' | 'V75' | 'V100';
  side: 'BUY' | 'SELL';
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  stopLoss?: number;
  takeProfit?: number;
  entryTime: string;
  htfContext: string;
  ltfContext: string;
  featuresUsed: string[];
  confidence: number;
}

export function EnhancedActiveTradesTable({ trades }: { trades: ActiveTrade[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticket</TableHead>
          <TableHead>Symbol</TableHead>
          <TableHead>Side</TableHead>
          <TableHead>Entry Price</TableHead>
          <TableHead>Current Price</TableHead>
          <TableHead>P&L</TableHead>
          <TableHead>HTF Context</TableHead>
          <TableHead>LTF Context</TableHead>
          <TableHead>Features</TableHead>
          <TableHead>Confidence</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((trade) => (
          <TableRow key={trade.ticket}>
            <TableCell>{trade.ticket}</TableCell>
            <TableCell>{trade.symbol}</TableCell>
            <TableCell>
              <Badge variant={trade.side === 'BUY' ? 'default' : 'destructive'}>
                {trade.side}
              </Badge>
            </TableCell>
            {/* More cells */}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### US-002: Implement Pending Signals with Approval Actions

**Description:** As a trader, I need to approve or reject pending trading signals.

**Acceptance Criteria:**
- [ ] Update `PendingSignals.tsx` to use real API data
- [ ] Display signal ID, symbol, signal type (STRONG_BUY, BUY, SELL, STRONG_SELL)
- [ ] Display confidence score
- [ ] Display HTF context
- [ ] Display evolved features used
- [ ] Display timestamp
- [ ] Add "Approve" button for each signal
- [ ] Add "Reject" button for each signal
- [ ] Add "Approve All" button
- [ ] Add "Reject All" button
- [ ] Show confirmation dialog before bulk actions
- [ ] Show success/error toast notifications
- [ ] Remove signal from list after action
- [ ] Add filtering by symbol
- [ ] Add sorting by confidence or time
- [ ] Typecheck passes
- [ ] Verify in browser that signal approval works

**Priority:** 2

**Technical Implementation:**

```typescript
// src/components/dashboard/PendingSignals.tsx
interface PendingSignal {
  signalId: string;
  symbol: string;
  signalType: 'STRONG_BUY' | 'BUY' | 'SELL' | 'STRONG_SELL';
  confidence: number;
  htfContext: string;
  timestamp: string;
  featuresUsed: string[];
}

export function PendingSignals({ signals }: { signals: PendingSignal[] }) {
  const handleApprove = async (signalId: string) => {
    try {
      await apiClient.post(`/trades/signals/${signalId}/approve`);
      toast.success('Signal approved');
      // Refresh signals
    } catch (error) {
      toast.error('Failed to approve signal');
    }
  };

  const handleReject = async (signalId: string) => {
    try {
      await apiClient.post(`/trades/signals/${signalId}/reject`);
      toast.success('Signal rejected');
      // Refresh signals
    } catch (error) {
      toast.error('Failed to reject signal');
    }
  };

  return (
    <div>
      {signals.map((signal) => (
        <Card key={signal.signalId}>
          <CardHeader>
            <CardTitle>{signal.symbol} - {signal.signalType}</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Signal details */}
            <div className="flex gap-2">
              <Button onClick={() => handleApprove(signal.signalId)}>Approve</Button>
              <Button onClick={() => handleReject(signal.signalId)} variant="destructive">
                Reject
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

### US-003: Implement Recent Trades History

**Description:** As a trader, I need to view my closed trade history.

**Acceptance Criteria:**
- [ ] Update `RecentTrades.tsx` to use real API data
- [ ] Display ticket ID, symbol, side
- [ ] Display entry and exit prices
- [ ] Display final P&L
- [ ] Display entry and exit times
- [ ] Display trade duration
- [ ] Display outcome (WIN/LOSS)
- [ ] Display HTF/LTF context
- [ ] Display features used
- [ ] Color-code outcomes (green=WIN, red=LOSS)
- [ ] Add filtering by symbol
- [ ] Add filtering by outcome
- [ ] Add date range selector
- [ ] Add pagination (20 trades per page)
- [ ] Add export to CSV button
- [ ] Add trade detail view on row click
- [ ] Typecheck passes
- [ ] Verify in browser that recent trades display correctly

**Priority:** 3

**Technical Implementation:**

```typescript
// src/components/dashboard/RecentTrades.tsx
interface ClosedTrade {
  ticket: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  entryTime: string;
  exitTime: string;
  outcome: 'WIN' | 'LOSS';
  htfContext: string;
  ltfContext: string;
  featuresUsed: string[];
}

export function RecentTrades({ trades }: { trades: ClosedTrade[] }) {
  const [filter, setFilter] = useState<string>('all');
  const [page, setPage] = useState(1);

  const filteredTrades = trades.filter(trade => {
    if (filter === 'all') return true;
    return trade.outcome.toLowerCase() === filter;
  });

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger>
            <SelectValue placeholder="Filter by outcome" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Trades</SelectItem>
            <SelectItem value="win">Winning Trades</SelectItem>
            <SelectItem value="loss">Losing Trades</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Table>
        {/* Trade list */}
      </Table>

      <Pagination>
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious onClick={() => setPage(p => Math.max(1, p - 1))} />
          </PaginationItem>
          <PaginationItem>
            <PaginationNext onClick={() => setPage(p => p + 1)} />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}
```

### US-004: Implement Real-Time Execution Log

**Description:** As a trader, I need to see real-time trade execution events.

**Acceptance Criteria:**
- [ ] Update `ExecutionLog.tsx` to use real WebSocket data
- [ ] Display timestamp for each event
- [ ] Display event type (EXECUTION, SIGNAL_GENERATED, APPROVAL, REJECTION)
- [ ] Display symbol
- [ ] Display action (BUY/SELL)
- [ ] Display status (SUCCESS, FAILURE, PENDING)
- [ ] Display message
- [ ] Auto-scroll to show newest events
- [ ] Add color coding for event types (green=SUCCESS, red=FAILURE, blue=PENDING)
- [ ] Add event filtering by type
- [ ] Add event filtering by symbol
- [ ] Add pause/resume button
- [ ] Add clear log button
- [ ] Add export log button
- [ ] Limit log to 100 most recent events
- [ ] Typecheck passes
- [ ] Verify in browser that execution log updates in real-time

**Priority:** 3

**Technical Implementation:**

```typescript
// src/components/dashboard/ExecutionLog.tsx
interface ExecutionEvent {
  timestamp: string;
  eventType: 'EXECUTION' | 'SIGNAL_GENERATED' | 'APPROVAL' | 'REJECTION';
  symbol: string;
  action: 'BUY' | 'SELL';
  status: 'SUCCESS' | 'FAILURE' | 'PENDING';
  message: string;
}

export function ExecutionLog() {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleExecutionEvent = (event: WSEvent<ExecutionEvent>) => {
      if (paused) return;
      setEvents(prev => [event.data, ...prev].slice(0, 100));
    };

    wsClient.on('execution_event', handleExecutionEvent);
    return () => wsClient.off('execution_event', handleExecutionEvent);
  }, [paused]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events]);

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Execution Log</CardTitle>
          <div className="flex gap-2">
            <Button onClick={() => setPaused(!paused)} variant="outline">
              {paused ? 'Resume' : 'Pause'}
            </Button>
            <Button onClick={() => setEvents([])} variant="outline">
              Clear
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div ref={scrollRef} className="h-96 overflow-y-auto space-y-2">
          {events.map((event, i) => (
            <div key={i} className="text-sm p-2 bg-muted rounded">
              <span className="text-muted-foreground">{event.timestamp}</span>
              <Badge>{event.eventType}</Badge>
              <span>{event.symbol} {event.action}</span>
              <span className={event.status === 'SUCCESS' ? 'text-green-500' : 'text-red-500'}>
                {event.status}
              </span>
              <span>{event.message}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-005: Add Trade Detail Modal

**Description:** As a trader, I need detailed information about a specific trade.

**Acceptance Criteria:**
- [ ] Create `TradeDetailModal.tsx` component
- [ ] Display all trade information in modal
- [ ] Show trade ticket, symbol, side
- [ ] Show entry/exit prices and times
- [ ] Show P&L with percentage
- [ ] Show stop loss and take profit levels
- [ ] Show HTF/LTF context with explanation
- [ ] Show all evolved features used with descriptions
- [ ] Show confidence score breakdown
- [ ] Show trade duration
- [ ] Show chart of price movement during trade (if available)
- [ ] Add close button
- [ ] Add "View Similar Trades" link
- [ ] Typecheck passes
- [ ] Verify in browser that modal displays correctly

**Priority:** 4

**Technical Implementation:**

```typescript
// src/components/dashboard/TradeDetailModal.tsx
export function TradeDetailModal({ trade, open, onClose }: TradeDetailModalProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Trade Details - {trade.ticket}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4">
          {/* Trade Summary */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Symbol</Label>
              <div>{trade.symbol}</div>
            </div>
            <div>
              <Label>Side</Label>
              <Badge>{trade.side}</Badge>
            </div>
            <div>
              <Label>Entry Price</Label>
              <div>{trade.entryPrice.toFixed(2)}</div>
            </div>
            <div>
              <Label>Current Price</Label>
              <div>{trade.currentPrice.toFixed(2)}</div>
            </div>
          </div>

          {/* P&L */}
          <div>
            <Label>Profit & Loss</Label>
            <div className={`text-2xl font-bold ${trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${trade.pnl.toFixed(2)}
            </div>
          </div>

          {/* Context */}
          <div>
            <Label>HTF Context</Label>
            <div>{trade.htfContext}</div>
          </div>

          {/* Features */}
          <div>
            <Label>Evolved Features Used</Label>
            <div className="flex flex-wrap gap-2">
              {trade.featuresUsed.map(feature => (
                <Badge key={feature} variant="outline">{feature}</Badge>
              ))}
            </div>
          </div>

          {/* Confidence */}
          <div>
            <Label>Confidence Score</Label>
            <Progress value={trade.confidence * 100} />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### US-006: Add Trade Filtering and Search

**Description:** As a trader, I need to filter and search through trades.

**Acceptance Criteria:**
- [ ] Add search input to filter by ticket ID or symbol
- [ ] Add filter dropdown for symbol (V10, V25, V50, V75, V100)
- [ ] Add filter dropdown for side (BUY, SELL, All)
- [ ] Add filter dropdown for profit/loss (profitable, losing, all)
- [ ] Add date range picker for trade time
- [ ] Add sort options (by time, by P&L, by confidence)
- [ ] Add clear filters button
- [ ] Show active filter count
- [ ] Persist filters in URL query params
- [ ] Typecheck passes
- [ ] Verify in browser that filtering works correctly

**Priority:** 5

**Technical Implementation:**

```typescript
// src/hooks/useTradeFilters.ts
export function useTradeFilters() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [filters, setFilters] = useState({
    search: searchParams.get('search') || '',
    symbol: searchParams.get('symbol') || 'all',
    side: searchParams.get('side') || 'all',
    pnl: searchParams.get('pnl') || 'all',
  });

  const updateFilter = (key: string, value: string) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);

    const params = new URLSearchParams();
    Object.entries(newFilters).forEach(([k, v]) => {
      if (v && v !== 'all') params.set(k, v);
    });

    router.push(`?${params.toString()}`, { scroll: false });
  };

  const clearFilters = () => {
    setFilters({ search: '', symbol: 'all', side: 'all', pnl: 'all' });
    router.push('', { scroll: false });
  };

  return { filters, updateFilter, clearFilters };
}
```

### US-007: Add Manual Trade Controls

**Description:** As a trader, I need to manually close trades or modify stops.

**Acceptance Criteria:**
- [ ] Add "Close Trade" button to each active trade row
- [ ] Add "Modify Stop Loss" button
- [ ] Add "Modify Take Profit" button
- [ ] Show confirmation dialog before closing
- [ ] Show input dialog for modifying stops
- [ ] Validate stop loss/take profit values
- [ ] Show success/error notifications
- [ ] Update trade after modification
- [ ] Require trader role or higher
- [ ] Typecheck passes
- [ ] Verify in browser that controls work correctly

**Priority:** 6

**Technical Implementation:**

```typescript
// src/components/dashboard/TradeControls.tsx
export function TradeControls({ trade }: { trade: ActiveTrade }) {
  const { can } = usePermissions();

  const handleCloseTrade = async () => {
    const confirmed = await confirm('Are you sure you want to close this trade?');
    if (!confirmed) return;

    try {
      await apiClient.post(`/trades/${trade.ticket}/close`);
      toast.success('Trade closed successfully');
    } catch (error) {
      toast.error('Failed to close trade');
    }
  };

  const handleModifyStop = async () => {
    const newStop = prompt('Enter new stop loss:', trade.stopLoss?.toString());
    if (!newStop) return;

    try {
      await apiClient.put(`/trades/${trade.ticket}`, { stopLoss: parseFloat(newStop) });
      toast.success('Stop loss updated');
    } catch (error) {
      toast.error('Failed to update stop loss');
    }
  };

  if (!can('control:trading')) return null;

  return (
    <div className="flex gap-2">
      <Button onClick={handleCloseTrade} variant="destructive" size="sm">
        Close
      </Button>
      <Button onClick={handleModifyStop} variant="outline" size="sm">
        Modify Stop
      </Button>
    </div>
  );
}
```

### US-008: Implement Trade Statistics Summary

**Description:** As a trader, I need to see summary statistics for my trades.

**Acceptance Criteria:**
- [ ] Create `TradeStatistics.tsx` component
- [ ] Display total trades count
- [ ] Display active trades count
- [ ] Display win rate percentage
- [ ] Display average win amount
- [ ] Display average loss amount
- [ ] Display profit factor
- [ ] Display largest winning trade
- [ ] Display largest losing trade
- [ ] Display average trade duration
- [ ] Show statistics for filtered trades
- [ ] Add refresh button
- [ ] Typecheck passes
- [ ] Verify in browser that statistics display correctly

**Priority:** 7

**Technical Implementation:**

```typescript
// src/components/dashboard/TradeStatistics.tsx
export function TradeStatistics({ trades }: { trades: Trade[] }) {
  const stats = useMemo(() => {
    const winning = trades.filter(t => t.pnl > 0);
    const losing = trades.filter(t => t.pnl < 0);

    return {
      total: trades.length,
      active: trades.filter(t => t.status === 'active').length,
      winRate: trades.length > 0 ? (winning.length / trades.length) * 100 : 0,
      avgWin: winning.length > 0 ? winning.reduce((s, t) => s + t.pnl, 0) / winning.length : 0,
      avgLoss: losing.length > 0 ? losing.reduce((s, t) => s + t.pnl, 0) / losing.length : 0,
      profitFactor: calculateProfitFactor(winning, losing),
      largestWin: Math.max(...winning.map(t => t.pnl), 0),
      largestLoss: Math.min(...losing.map(t => t.pnl), 0),
    };
  }, [trades]);

  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard label="Total Trades" value={stats.total} />
      <MetricCard label="Active Trades" value={stats.active} />
      <MetricCard label="Win Rate" value={`${stats.winRate.toFixed(1)}%`} />
      <MetricCard label="Avg Win" value={`$${stats.avgWin.toFixed(2)}`} />
      <MetricCard label="Avg Loss" value={`$${stats.avgLoss.toFixed(2)}`} />
      <MetricCard label="Profit Factor" value={stats.profitFactor.toFixed(2)} />
      <MetricCard label="Largest Win" value={`$${stats.largestWin.toFixed(2)}`} />
      <MetricCard label="Largest Loss" value={`$${stats.largestLoss.toFixed(2)}`} />
    </div>
  );
}
```

## Functional Requirements

- FR-1: Active trades must update in real-time via WebSocket
- FR-2: Pending signals must show approval/rejection buttons
- FR-3: Recent trades must support filtering and pagination
- FR-4: Execution log must auto-scroll to show newest events
- FR-5: Trade details must be viewable in modal
- FRR-6: Filters must persist in URL for shareability
- FR-7: Manual trade controls must require trader role
- FR-8: All monetary values must display with 2 decimal places
- FR-9: All timestamps must display in user's local timezone
- FR-10: P&L must be color-coded (green=profit, red=loss)

## Non-Goals

- No manual trade entry (system generates all trades)
- No backtesting or simulation mode
- No trade copying or social trading
- No advanced order types (trailing stops, OCO orders)
- No position sizing calculator
- No trade journal or notes

## Technical Considerations

### API Endpoints Required
- `GET /trades/active` - List active trades
- `GET /trades/recent?limit=20` - List recent trades
- `GET /trades/{ticket}` - Get trade details
- `POST /trades/signals/{id}/approve` - Approve signal
- `POST /trades/signals/{id}/reject` - Reject signal
- `POST /trades/{ticket}/close` - Close trade
- `PUT /trades/{ticket}` - Modify trade (stop loss, take profit)
- `GET /trades/statistics` - Get trade statistics

### WebSocket Events Required
- `trade_update` - Price/P&L update for active trade
- `new_signal` - New pending signal
- `signal_approved` - Signal approved
- `signal_rejected` - Signal rejected
- `trade_closed` - Trade closed
- `execution_event` - Trade execution event

### Performance Requirements
- Active trades list must update within 500ms of WebSocket event
- Execution log must display events within 100ms of receipt
- Trade detail modal must open within 100ms of click
- Filters must apply within 200ms of selection

### Data Validation
- All ticket IDs must be validated format
- All prices must be positive numbers
- All P&L values must be numbers
- All timestamps must be valid ISO 8601 dates
- All confidence scores must be 0-1

## Success Metrics

- Active trades update latency < 500ms
- Signal approval success rate > 99%
- Trade close execution time < 1 second
- Zero data loss in execution log
- Filter response time < 200ms
- User satisfaction with trade detail view > 4.5/5

## Implementation Order

1. US-001: Update Active Trades Table with Real Data
2. US-002: Implement Pending Signals with Approval Actions
3. US-004: Implement Real-Time Execution Log
4. US-003: Implement Recent Trades History
5. US-005: Add Trade Detail Modal
6. US-006: Add Trade Filtering and Search
7. US-008: Implement Trade Statistics Summary
8. US-007: Add Manual Trade Controls

## Testing Strategy

### Unit Tests
- Test trade data formatting
- Test P&L calculations
- Test filter logic
- Test sorting logic

### Integration Tests
- Test trade approval flow
- Test trade rejection flow
- Test trade close flow
- Test filter persistence

### Manual Testing
- Verify all active trades display
- Test signal approval/rejection
- Test trade detail modal
- Test all filters and search
- Test manual trade controls
- Verify real-time updates work

### Load Testing
- Test with 100+ active trades
- Test with high-frequency execution events
- Test filter performance with large datasets

## Known Issues & Risks

- Real-time updates may lag with many active trades
- Trade approval may have race conditions
- WebSocket disconnection may cause data inconsistency
- Large trade history may impact performance
- Manual trade controls need careful permission handling

## Related PRDs

- PRD: Backend API Integration (trading endpoints)
- PRD: WebSocket Integration (real-time updates)
- PRD: Authentication & User Management (permissions)
- PRD: Analytics & Performance Features (trade metrics)
- PRD: System Control Features (auto-trading toggle)
