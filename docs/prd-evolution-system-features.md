# PRD: Evolution System Features

## Overview

The Evolution System is the core differentiator of the EURABAY Living System. It implements a genetic algorithm that evolves trading features over generations, with complete transparency into the evolutionary process. This PRD implements the full UI and integration for the evolution system.

## Goals

- Display real-time evolution metrics (current generation, controller decision)
- Show generation history with fitness progression
- Visualize feature success rates and performance
- Track mutation strategy effectiveness
- Display controller decision timeline with reasoning
- Show evolution event log in real-time
- Allow manual evolution trigger
- Display evolved features used in each trade
- Provide complete transparency into evolutionary process

## Current State

**Problem:**
- Evolution components exist but use mock data
- No connection to actual evolution engine
- Evolution parameters not adjustable
- No manual evolution trigger
- Missing evolution detail views
- No feature performance tracking
- Missing mutation analysis

**Impact:**
- Cannot monitor actual evolution progress
- Cannot understand which features work best
- Cannot tune evolution parameters
- System appears to evolve but doesn't
- Missing key "living system" transparency

## User Stories

### US-001: Update Evolution Metrics with Real Data

**Description:** As a user, I need to see current evolution status and metrics.

**Acceptance Criteria:**
- [ ] Update `EvolutionMetrics.tsx` to use real API data
- [ ] Display current generation number
- [ ] Display controller decision with badge color coding:
  - STABLE: Green
  - EVOLVE_CONSERVATIVE: Yellow
  - EVOLVE_MODERATE: Orange
  - EVOLVE_AGGRESSIVE: Red
- [ ] Display cycles completed
- [ ] Display system version
- [ ] Display birth time
- [ ] Display uptime counter
- [ ] Add refresh button
- [ ] Add auto-refresh every 5 seconds
- [ ] Add loading state
- [ ] Add error state with retry
- [ ] Typecheck passes
- [ ] Verify in browser that metrics display correctly

**Priority:** 1

**Technical Implementation:**

```typescript
// src/components/dashboard/EvolutionMetrics.tsx
export function EvolutionMetrics() {
  const { metrics, loading, error } = useEvolutionData();

  if (loading) return <Skeleton />;
  if (error) return <ErrorState error={error} />;

  const decisionColors = {
    STABLE: 'bg-green-500',
    EVOLVE_CONSERVATIVE: 'bg-yellow-500',
    EVOLVE_MODERATE: 'bg-orange-500',
    EVOLVE_AGGRESSIVE: 'bg-red-500',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evolution Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Generation</Label>
            <div className="text-2xl font-bold">{metrics.currentGeneration}</div>
          </div>
          <div>
            <Label>Controller Decision</Label>
            <Badge className={decisionColors[metrics.controllerDecision]}>
              {metrics.controllerDecision}
            </Badge>
          </div>
          <div>
            <Label>Cycles Completed</Label>
            <div>{metrics.cyclesCompleted.toLocaleString()}</div>
          </div>
          <div>
            <Label>System Uptime</Label>
            <div>{metrics.uptime}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-002: Implement Generation History Chart

**Description:** As a user, I need to see evolution progression over time.

**Acceptance Criteria:**
- [ ] Update `GenerationHistoryChart.tsx` to use real API data
- [ ] Display line chart with generation number on X-axis
- [ ] Display fitness score on Y-axis
- [ ] Display average performance as secondary line
- [ ] Show tooltips with generation details on hover
- [ ] Highlight current generation
- [ ] Add zoom/pan functionality
- [ ] Add date range selector (7 days, 30 days, 90 days, all)
- [ ] Show fitness improvement percentage
- [ ] Add auto-refresh every 10 seconds
- [ ] Typecheck passes
- [ ] Verify in browser that chart displays correctly

**Priority:** 2

**Technical Implementation:**

```typescript
// src/components/dashboard/GenerationHistoryChart.tsx
export function GenerationHistoryChart() {
  const { history, loading } = useEvolutionData();
  const [range, setRange] = useState<number>(7);

  const filteredHistory = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - range);
    return history.filter(h => new Date(h.timestamp) >= cutoff);
  }, [history, range]);

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Generation History</CardTitle>
          <Select value={range.toString()} onValueChange={(v) => setRange(parseInt(v))}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 Days</SelectItem>
              <SelectItem value="30">30 Days</SelectItem>
              <SelectItem value="90">90 Days</SelectItem>
              <SelectItem value="0">All Time</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={filteredHistory}>
            <XAxis dataKey="generation" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="fitness" stroke="#8884d8" name="Fitness" />
            <Line type="monotone" dataKey="avgPerformance" stroke="#82ca9d" name="Avg Performance" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

### US-003: Implement Feature Success Analysis

**Description:** As a user, I need to see which evolved features perform best.

**Acceptance Criteria:**
- [ ] Update `FeatureSuccessChart.tsx` to use real API data
- [ ] Display bar chart with feature names
- [ ] Show success rate percentage
- [ ] Show total uses count
- [ ] Show win/loss counts
- [ ] Show average P&L per feature
- [ ] Color-code by success rate (green >70%, yellow 50-70%, red <50%)
- [ ] Add sorting by success rate, uses, or P&L
- [ ] Add filtering by minimum uses
- [ ] Show tooltips with detailed stats on hover
- [ ] Add "View Feature Details" button
- [ ] Add auto-refresh every 10 seconds
- [ ] Typecheck passes
- [ ] Verify in browser that chart displays correctly

**Priority:** 2

**Technical Implementation:**

```typescript
// src/components/dashboard/FeatureSuccessChart.tsx
export function FeatureSuccessChart() {
  const { features, loading } = useEvolutionData();
  const [sortBy, setSortBy] = useState<'successRate' | 'totalUses' | 'avgPnL'>('successRate');
  const [minUses, setMinUses] = useState<number>(10);

  const filteredFeatures = useMemo(() => {
    return features
      .filter(f => f.totalUses >= minUses)
      .sort((a, b) => b[sortBy] - a[sortBy]);
  }, [features, sortBy, minUses]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Feature Success Analysis</CardTitle>
        <div className="flex gap-2">
          <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
            <SelectTrigger>
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="successRate">Success Rate</SelectItem>
              <SelectItem value="totalUses">Total Uses</SelectItem>
              <SelectItem value="avgPnL">Avg P&L</SelectItem>
            </SelectContent>
          </Select>
          <Input
            type="number"
            placeholder="Min uses"
            value={minUses}
            onChange={(e) => setMinUses(parseInt(e.target.value))}
          />
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={filteredFeatures}>
            <XAxis dataKey="featureName" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="successRate" fill="#c4f54d" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

### US-004: Implement Mutation Success Tracking

**Description:** As a user, I need to see which mutation strategies work best.

**Acceptance Criteria:**
- [ ] Update `MutationSuccessChart.tsx` to use real API data
- [ ] Display pie or donut chart showing mutation distribution
- [ ] Show success rate for each mutation type
- [ ] Show total attempts count
- [ ] Show successful attempts count
- [ ] Show average fitness improvement
- [ ] Add detailed table view
- [ ] Color-code by success rate
- [ ] Add sorting options
- [ ] Add auto-refresh every 10 seconds
- [ ] Typecheck passes
- [ ] Verify in browser that chart displays correctly

**Priority:** 3

**Technical Implementation:**

```typescript
// src/components/dashboard/MutationSuccessChart.tsx
export function MutationSuccessChart() {
  const { mutations, loading } = useEvolutionData();

  const COLORS = ['#c4f54d', '#66bb6a', '#ffa726', '#ef5350', '#29b6f6'];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mutation Success Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={mutations}
              dataKey="totalAttempts"
              nameKey="mutationType"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label
            >
              {mutations.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mutation Type</TableHead>
              <TableHead>Success Rate</TableHead>
              <TableHead>Attempts</TableHead>
              <TableHead>Avg Fitness Gain</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mutations.map((mutation) => (
              <TableRow key={mutation.mutationType}>
                <TableCell>{mutation.mutationType}</TableCell>
                <TableCell>{mutation.successRate.toFixed(1)}%</TableCell>
                <TableCell>{mutation.totalAttempts}</TableCell>
                <TableCell>+{mutation.avgFitnessImprovement.toFixed(1)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
```

### US-005: Implement Controller Decision Timeline

**Description:** As a user, I need to see controller decisions over time with reasoning.

**Acceptance Criteria:**
- [ ] Update `ControllerDecisionTimeline.tsx` to use real API data
- [ ] Display vertical timeline with decision events
- [ ] Show decision type with color coding
- [ ] Show timestamp
- [ ] Show performance metric at time of decision
- [ ] Show decision reason/explanation
- [ ] Add filtering by decision type
- [ ] Add date range selector
- [ ] Add search in reasons
- [ ] Show decision statistics (count by type)
- [ ] Add auto-refresh every 10 seconds
- [ ] Typecheck passes
- [ ] Verify in browser that timeline displays correctly

**Priority:** 3

**Technical Implementation:**

```typescript
// src/components/dashboard/ControllerDecisionTimeline.tsx
export function ControllerDecisionTimeline() {
  const { decisions, loading } = useEvolutionData();
  const [filter, setFilter] = useState<string>('all');

  const filteredDecisions = useMemo(() => {
    if (filter === 'all') return decisions;
    return decisions.filter(d => d.decision === filter);
  }, [decisions, filter]);

  const decisionColors = {
    STABLE: 'border-green-500',
    EVOLVE_CONSERVATIVE: 'border-yellow-500',
    EVOLVE_MODERATE: 'border-orange-500',
    EVOLVE_AGGRESSIVE: 'border-red-500',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Controller Decision Timeline</CardTitle>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger>
            <SelectValue placeholder="Filter by decision" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Decisions</SelectItem>
            <SelectItem value="STABLE">Stable</SelectItem>
            <SelectItem value="EVOLVE_CONSERVATIVE">Evolve Conservative</SelectItem>
            <SelectItem value="EVOLVE_MODERATE">Evolve Moderate</SelectItem>
            <SelectItem value="EVOLVE_AGGRESSIVE">Evolve Aggressive</SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {filteredDecisions.map((decision, i) => (
            <div key={i} className={`flex gap-4 p-4 border-l-4 ${decisionColors[decision.decision]}`}>
              <div className="flex-1">
                <div className="flex justify-between">
                  <Badge>{decision.decision}</Badge>
                  <span className="text-sm text-muted-foreground">
                    {new Date(decision.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="mt-2">
                  <div className="text-sm font-medium">Performance: {decision.performance.toFixed(1)}%</div>
                  <div className="text-sm text-muted-foreground">{decision.reason}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-006: Implement Evolution Event Log

**Description:** As a user, I need to see real-time evolution events.

**Acceptance Criteria:**
- [ ] Update `EvolutionLogViewer.tsx` to use real WebSocket data
- [ ] Display events in reverse chronological order
- [ ] Show event type with badge (MUTATION, EVOLUTION_CYCLE, FEATURE_SUCCESS, FEATURE_FAILURE)
- [ ] Show generation number
- [ ] Show timestamp
- [ ] Show event message
- [ ] Show event details in expandable section
- [ ] Color-code by event type
- [ ] Add filtering by event type
- [ ] Add search in messages
- [ ] Add pause/resume button
- [ ] Auto-scroll to show newest events
- [ ] Limit to 100 most recent events
- [ ] Add export log button
- [ ] Add clear log button
- [ ] Typecheck passes
- [ ] Verify in browser that log updates in real-time

**Priority:** 4

**Technical Implementation:**

```typescript
// src/components/dashboard/EvolutionLogViewer.tsx
export function EvolutionLogViewer() {
  const [events, setEvents] = useState<EvolutionLog[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEvolutionEvent = (event: WSEvent<EvolutionLog>) => {
      if (paused) return;
      setEvents(prev => [event.data, ...prev].slice(0, 100));
    };

    wsClient.on('evolution_event', handleEvolutionEvent);
    return () => wsClient.off('evolution_event', handleEvolutionEvent);
  }, [paused]);

  useEffect(() => {
    if (scrollRef.current && !paused) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events, paused]);

  const filteredEvents = useMemo(() => {
    if (filter === 'all') return events;
    return events.filter(e => e.type === filter);
  }, [events, filter]);

  const eventColors = {
    MUTATION: 'bg-blue-500',
    EVOLUTION_CYCLE: 'bg-purple-500',
    FEATURE_SUCCESS: 'bg-green-500',
    FEATURE_FAILURE: 'bg-red-500',
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Evolution Log</CardTitle>
          <div className="flex gap-2">
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Events</SelectItem>
                <SelectItem value="MUTATION">Mutations</SelectItem>
                <SelectItem value="EVOLUTION_CYCLE">Evolution Cycles</SelectItem>
                <SelectItem value="FEATURE_SUCCESS">Feature Success</SelectItem>
                <SelectItem value="FEATURE_FAILURE">Feature Failures</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={() => setPaused(!paused)} variant="outline">
              {paused ? 'Resume' : 'Pause'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div ref={scrollRef} className="h-96 overflow-y-auto space-y-2">
          {filteredEvents.map((event, i) => (
            <div key={i} className="p-3 bg-muted rounded">
              <div className="flex justify-between items-start">
                <Badge className={eventColors[event.type]}>{event.type}</Badge>
                <span className="text-xs text-muted-foreground">
                  {new Date(event.timestamp).toLocaleString()}
                </span>
              </div>
              <div className="mt-1 text-sm">Gen {event.generation}: {event.message}</div>
              {event.details && (
                <Collapsible>
                  <CollapsibleTrigger className="text-xs text-muted-foreground">
                    Show Details
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <pre className="text-xs bg-background p-2 mt-2 rounded">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-007: Implement Evolution Parameter Controls

**Description:** As an admin, I need to adjust evolution parameters.

**Acceptance Criteria:**
- [ ] Update `EvolutionParameters.tsx` to use real API
- [ ] Add slider/input for mutation rate (0-1)
- [ ] Add slider/input for adaptive min accuracy threshold (0-1)
- [ ] Add slider/input for min performance threshold (0-1)
- [ ] Add slider/input for evolution aggression (0-1)
- [ ] Display current value for each parameter
- [ ] Add parameter descriptions/tooltip
- [ ] Add "Save Changes" button
- [ ] Add "Reset to Defaults" button
- [ ] Show unsaved changes indicator
- [ ] Validate input ranges
- [ ] Show success/error notifications
- [ ] Require admin role
- [ ] Typecheck passes
- [ ] Verify in browser that controls work correctly

**Priority:** 5

**Technical Implementation:**

```typescript
// src/components/dashboard/EvolutionParameters.tsx
export function EvolutionParameters() {
  const { can } = usePermissions();
  const [params, setParams] = useState<EvolutionParams | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchEvolutionParams().then(setParams);
  }, []);

  const handleSave = async () => {
    try {
      await apiClient.post('/evolution/parameters', params);
      toast.success('Evolution parameters updated');
      setHasChanges(false);
    } catch (error) {
      toast.error('Failed to update parameters');
    }
  };

  const handleReset = async () => {
    const defaults = await fetchEvolutionParams();
    setParams(defaults);
    setHasChanges(true);
  };

  if (!can('admin:evolution')) {
    return <div>Admin access required</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evolution Parameters</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div>
            <div className="flex justify-between">
              <Label>Mutation Rate</Label>
              <span>{params?.mutationRate.toFixed(2)}</span>
            </div>
            <Slider
              value={[params?.mutationRate || 0]}
              onValueChange={([v]) => {
                setParams(p => p ? { ...p, mutationRate: v } : null);
                setHasChanges(true);
              }}
              min={0}
              max={1}
              step={0.01}
            />
          </div>

          {/* More parameter controls */}

          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={!hasChanges}>
              Save Changes
            </Button>
            <Button onClick={handleReset} variant="outline">
              Reset to Defaults
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### US-008: Add Manual Evolution Trigger

**Description:** As an admin, I need to manually trigger an evolution cycle.

**Acceptance Criteria:**
- [ ] Add "Force Evolution" button to evolution section
- [ ] Show confirmation dialog before triggering
- [ ] Display warning about performance impact
- [ ] Call API to trigger evolution
- [ ] Show loading state during evolution
- [ ] Show success/error notification
- [ ] Update generation number after evolution
- [ ] Add evolution cooldown (e.g., 5 minutes minimum between forced evolutions)
- [ ] Log forced evolution in event log
- [ ] Require admin role
- [ ] Typecheck passes
- [ ] Verify in browser that trigger works correctly

**Priority:** 6

**Technical Implementation:**

```typescript
// src/components/dashboard/ForceEvolutionButton.tsx
export function ForceEvolutionButton() {
  const { can } = usePermissions();
  const [loading, setLoading] = useState(false);
  const [lastEvolution, setLastEvolution] = useState<number>(0);

  const handleForceEvolution = async () => {
    const confirmed = await confirm(
      'Are you sure you want to force an evolution cycle? This may impact trading performance.'
    );
    if (!confirmed) return;

    setLoading(true);
    try {
      const result = await apiClient.post('/system/force-evolution');
      toast.success(`Evolution cycle initiated. New generation: ${result.generation}`);
      setLastEvolution(Date.now());
    } catch (error) {
      toast.error('Failed to trigger evolution');
    } finally {
      setLoading(false);
    }
  };

  const cooldownRemaining = Math.max(0, 5 * 60 * 1000 - (Date.now() - lastEvolution));
  const canEvolve = can('admin:evolution') && cooldownRemaining === 0;

  return (
    <Button
      onClick={handleForceEvolution}
      disabled={!canEvolve || loading}
      variant="destructive"
    >
      {loading ? 'Evolving...' : 'Force Evolution'}
      {cooldownRemaining > 0 && ` (${Math.ceil(cooldownRemaining / 1000)}s)`}
    </Button>
  );
}
```

### US-009: Add Feature Detail View

**Description:** As a user, I need detailed information about a specific evolved feature.

**Acceptance Criteria:**
- [ ] Create `FeatureDetailModal.tsx` component
- [ ] Display feature name and ID
- [ ] Display feature description (if available)
- [ ] Display success rate with trend
- [ ] Display total uses and win/loss counts
- [ ] Display average P&L
- [ ] Display performance over time chart
- [ ] Display recent trades using this feature
- [ ] Display mutation history for this feature
- [ ] Display feature parameters (if applicable)
- [ ] Add "Disable Feature" button (admin only)
- [ ] Add "View Similar Features" link
- [ ] Typecheck passes
- [ ] Verify in browser that modal displays correctly

**Priority:** 7

**Technical Implementation:**

```typescript
// src/components/dashboard/FeatureDetailModal.tsx
export function FeatureDetailModal({ feature, open, onClose }: FeatureDetailModalProps) {
  const { can } = usePermissions();
  const [details, setDetails] = useState<FeatureDetails | null>(null);

  useEffect(() => {
    if (open) {
      fetchFeatureDetails(feature.featureId).then(setDetails);
    }
  }, [open, feature.featureId]);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{feature.featureName}</DialogTitle>
        </DialogHeader>

        {details && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-4 gap-4">
              <MetricCard label="Success Rate" value={`${details.successRate.toFixed(1)}%`} />
              <MetricCard label="Total Uses" value={details.totalUses} />
              <MetricCard label="Wins" value={details.wins} />
              <MetricCard label="Losses" value={details.losses} />
              <MetricCard label="Avg P&L" value={`$${details.avgPnL.toFixed(2)}`} />
            </div>

            {/* Performance Chart */}
            <div>
              <h3 className="text-lg font-semibold mb-2">Performance Over Time</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={details.performanceHistory}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="successRate" stroke="#c4f54d" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Recent Trades */}
            <div>
              <h3 className="text-lg font-semibold mb-2">Recent Trades</h3>
              <Table>
                <TableBody>
                  {details.recentTrades.map(trade => (
                    <TableRow key={trade.ticket}>
                      <TableCell>{trade.ticket}</TableCell>
                      <TableCell>{trade.symbol}</TableCell>
                      <TableCell>${trade.pnl.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Admin Controls */}
            {can('admin:evolution') && (
              <div className="flex gap-2">
                <Button variant="destructive">Disable Feature</Button>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## Functional Requirements

- FR-1: Evolution metrics must update in real-time via WebSocket
- FR-2: Generation history must display minimum 30 days of data
- FR-3: Feature success must include features with minimum 10 uses
- FR-4: Mutation success must show all mutation types
- FR-5: Controller decisions must include reasoning
- FR-6: Evolution log must display all event types
- FR-7: Evolution parameters must be adjustable by admin only
- FR-8: Force evolution must have 5-minute cooldown
- FR-9: All evolution data must be exportable
- FR-10: Feature details must show complete performance history

## Non-Goals

- No manual feature creation (evolution only)
- No feature sharing between users
- No evolution simulation/backtesting
- No genetic algorithm visualization (too complex)
- No feature comparison tools

## Technical Considerations

### API Endpoints Required
- `GET /evolution/metrics` - Current evolution metrics
- `GET /evolution/generation-history?days=30` - Generation history
- `GET /evolution/feature-success` - Feature success rates
- `GET /evolution/mutation-success` - Mutation success rates
- `GET /evolution/controller-history?limit=50` - Controller decisions
- `GET /evolution/logs?limit=100&type=all` - Evolution logs
- `POST /evolution/parameters` - Update parameters
- `POST /system/force-evolution` - Trigger evolution
- `GET /evolution/features/{id}` - Feature details

### WebSocket Events Required
- `evolution_event` - All evolution events
- `generation_changed` - New generation started
- `controller_decision` - New controller decision
- `feature_mutated` - Feature was mutated
- `evolution_cycle_complete` - Evolution cycle finished

### Performance Requirements
- Evolution metrics must load within 1 second
- Charts must render within 500ms
- Event log must update within 100ms of event
- Parameter updates must complete within 500ms

### Data Validation
- Generation number must be positive integer
- Fitness scores must be 0-100
- Confidence scores must be 0-1
- Mutation rates must be 0-1
- All timestamps must be valid ISO 8601 dates

## Success Metrics

- Evolution metrics update latency < 500ms
- Event log displays 100% of events
- Parameter update success rate > 99%
- Force evolution completes within 10 seconds
- Feature detail view loads within 1 second
- User understands evolution process (survey)

## Implementation Order

1. US-001: Update Evolution Metrics with Real Data
2. US-002: Implement Generation History Chart
3. US-003: Implement Feature Success Analysis
4. US-004: Implement Mutation Success Tracking
5. US-005: Implement Controller Decision Timeline
6. US-006: Implement Evolution Event Log
7. US-007: Implement Evolution Parameter Controls
8. US-008: Add Manual Evolution Trigger
9. US-009: Add Feature Detail View

## Testing Strategy

### Unit Tests
- Test evolution data formatting
- Test fitness calculations
- Test mutation rate validation
- Test parameter range validation

### Integration Tests
- Test evolution parameter updates
- Test force evolution trigger
- Test feature detail loading
- Test event log subscriptions

### Manual Testing
- Verify all evolution metrics display
- Test all charts with various data ranges
- Test parameter adjustments
- Test force evolution
- Verify event log updates in real-time
- Test feature detail modal

### Load Testing
- Test with 100+ generations of history
- Test with 1000+ features
- Test with high-frequency evolution events

## Known Issues & Risks

- Evolution events may be very frequent during active evolution
- Large generation history may impact chart performance
- Force evolution may disrupt trading performance
- Parameter changes may have delayed effects
- Feature details may require complex backend queries

## Related PRDs

- PRD: Backend API Integration (evolution endpoints)
- PRD: WebSocket Integration (real-time events)
- PRD: Authentication & User Management (admin permissions)
- PRD: Trading System Features (feature usage in trades)
- PRD: Analytics & Performance Features (evolution metrics)
