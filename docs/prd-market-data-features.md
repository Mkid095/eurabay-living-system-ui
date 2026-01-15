# PRD: Market Data Features

## Overview

The EURABAY Living System trades Deriv.com volatility indices (V10, V25, V50, V75, V100). This PRD implements real-time market data display and analysis features for these markets.

## Goals

- Display real-time prices for all 5 volatility indices
- Show 24-hour price change percentages
- Display market overview with all symbols
- Show HTF trend analysis with confidence levels
- Display volatility levels
- Update prices in real-time via WebSocket
- Provide market regime information (R_10, R_25, etc.)

## Current State

**Problem:**
- `DerivMarketOverview.tsx` exists but uses mock data
- No real-time price updates
- No trend analysis display
- Missing market regime information
- No historical price charts

**Impact:**
- Cannot monitor actual market conditions
- Trading decisions based on fake data
- Missing critical market context
- System appears functional but shows no real markets

## User Stories

### US-001: Update Market Overview with Real Data

**Description:** As a trader, I need to see real-time prices for all volatility indices.

**Acceptance Criteria:**
- [ ] Update `DerivMarketOverview.tsx` to use real API data
- [ ] Display all 5 volatility indices (V10, V25, V50, V75, V100)
- [ ] Show current price for each symbol
- [ ] Show 24-hour price change percentage
- [ ] Color-code changes (green=up, red=down)
- [ ] Show volatility level
- [ ] Display trend direction (BULLISH/BEARISH)
- [ ] Add visual flash effect on price update
- [ ] Add auto-refresh every 3 seconds
- [ ] Add loading state
- [ ] Add error state with retry
- [ ] Typecheck passes
- [ ] Verify in browser that prices update in real-time

**Priority:** 1

**Technical Implementation:**

```typescript
// src/components/dashboard/DerivMarketOverview.tsx
export function DerivMarketOverview() {
  const { markets, loading, error } = useRealTimeMarkets();

  if (loading) return <MarketOverviewSkeleton />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="grid grid-cols-5 gap-4">
      {markets.map((market) => (
        <Card key={market.symbol}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{market.symbol}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{market.price.toFixed(2)}</div>
            <div className={`text-sm ${market.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {market.change_24h >= 0 ? '+' : ''}{market.change_24h.toFixed(2)}%
            </div>
            <Badge variant={market.trend === 'BULLISH' ? 'default' : 'destructive'}>
              {market.trend}
            </Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

### US-002: Add Market Detail View

**Description:** As a trader, I need detailed information about a specific market.

**Acceptance Criteria:**
- [ ] Create `MarketDetailModal.tsx` component
- [ ] Display symbol name and description
- [ ] Show current price with large font
- [ ] Show 24h high and low
- [ ] Show volume
- [ ] Show spread
- [ ] Show volatility index
- [ ] Show HTF trend with confidence
- [ ] Show market regime (R_10, R_25, etc.)
- [ ] Show recent price chart (last 100 bars)
- [ ] Show LTF trend
- [ ] Add support/resistance levels (if available)
- [ ] Typecheck passes
- [ ] Verify in browser that modal displays correctly

**Priority:** 2

**Technical Implementation:**

```typescript
// src/components/dashboard/MarketDetailModal.tsx
export function MarketDetailModal({ symbol, open, onClose }: MarketDetailModalProps) {
  const [details, setDetails] = useState<MarketDetail | null>(null);

  useEffect(() => {
    if (open) {
      fetchMarketDetail(symbol).then(setDetails);
    }
  }, [open, symbol]);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>{symbol} - Volatility Index</DialogTitle>
        </DialogHeader>

        {details && (
          <div className="space-y-6">
            {/* Price Info */}
            <div className="text-center">
              <div className="text-4xl font-bold">{details.price.toFixed(2)}</div>
              <div className={`text-lg ${details.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {details.change_24h >= 0 ? '+' : ''}{details.change_24h.toFixed(2)}%
              </div>
            </div>

            {/* Market Stats */}
            <div className="grid grid-cols-4 gap-4">
              <div>
                <Label>24h High</Label>
                <div>{details.high_24h.toFixed(2)}</div>
              </div>
              <div>
                <Label>24h Low</Label>
                <div>{details.low_24h.toFixed(2)}</div>
              </div>
              <div>
                <Label>Volume</Label>
                <div>{details.volume.toLocaleString()}</div>
              </div>
              <div>
                <Label>Spread</Label>
                <div>{details.spread.toFixed(1)}</div>
              </div>
            </div>

            {/* Trend Info */}
            <div>
              <Label>HTF Trend (H1)</Label>
              <Badge>{details.htf_trend}</Badge>
              <div>Confidence: {(details.htf_confidence * 100).toFixed(0)}%</div>
              <div>Regime: {details.regime}</div>
            </div>

            {/* Price Chart */}
            <div>
              <Label>Price History</Label>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={details.priceHistory}>
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="close" stroke="#c4f54d" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div        )}

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### US-003: Implement Market Trend Indicators

**Description:** As a trader, I need to see HTF trend analysis for each market.

**Acceptance Criteria:**
- [ ] Create `MarketTrendIndicator.tsx` component
- [ ] Display trend direction (BULLISH, BEARISH, NEUTRAL)
- [ ] Display confidence percentage
- [ ] Display market regime (R_10, R_25, R_50, R_75, R_100)
- [ ] Color-code trends (green=BULLISH, red=BEARISH, gray=NEUTRAL)
- [ ] Show trend strength indicator (weak, moderate, strong)
- [ ] Add trend history (last 10 H1 bars)
- [ ] Update in real-time via WebSocket
- [ ] Typecheck passes
- [ ] Verify in browser that trends display correctly

**Priority:** 3

**Technical Implementation:**

```typescript
// src/components/dashboard/MarketTrendIndicator.tsx
export function MarketTrendIndicator({ symbol }: { symbol: string }) {
  const [trend, setTrend] = useState<MarketTrend | null>(null);

  useEffect(() => {
    const handleMarketUpdate = (event: WSEvent<MarketUpdate>) => {
      if (event.data.symbol === symbol) {
        fetchMarketTrend(symbol).then(setTrend);
      }
    };

    wsClient.on('market_update', handleMarketUpdate);
    fetchMarketTrend(symbol).then(setTrend);

    return () => wsClient.off('market_update', handleMarketUpdate);
  }, [symbol]);

  if (!trend) return <Skeleton />;

  const trendConfig = {
    BULLISH: { color: 'text-green-500', icon: TrendingUp },
    BEARISH: { color: 'text-red-500', icon: TrendingDown },
    NEUTRAL: { color: 'text-gray-500', icon: Minus },
  };

  const config = trendConfig[trend.trend];
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-2">
      <Icon className={`h-4 w-4 ${config.color}`} />
      <span className={`font-medium ${config.color}`}>{trend.trend}</span>
      <span className="text-sm text-muted-foreground">
        ({(trend.confidence * 100).toFixed(0)}%)
      </span>
      <Badge variant="outline">{trend.regime}</Badge>
    </div>
  );
}
```

## Functional Requirements

- FR-1: All 5 volatility indices must display real-time prices
- FR-2: Price updates must be received within 500ms via WebSocket
- FR-3: 24-hour changes must be calculated from midnight UTC
- FR-4: Trends must be based on H1 timeframe analysis
- FR-5: Market regimes must match volatility index (V10=R_10, etc.)
- FR-6: All prices must display with 2 decimal places
- FR-7: All percentages must display with 2 decimal places

## Non-Goals

- No order book visualization
- No depth of market display
- No fundamental analysis
- No news integration
- No correlation matrix
- No heat map

## API Endpoints Required

- `GET /markets/overview` - All markets summary
- `GET /markets/{symbol}/data?timeframe=H1&bars=100` - Historical data
- `GET /markets/{symbol}/trend` - Trend analysis

## Success Metrics

- Price update latency < 500ms
- All markets display 100% of the time
- Trend accuracy > 80%
