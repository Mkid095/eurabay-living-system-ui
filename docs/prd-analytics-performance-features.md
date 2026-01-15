# PRD: Analytics & Performance Features

## Overview

This PRD implements the analytics and performance tracking features that display trading metrics, equity curves, and P&L history.

## Goals

- Display performance metrics (Sharpe ratio, max drawdown, etc.)
- Show equity curve chart
- Display P&L history
- Track performance over time
- Provide performance comparisons

## User Stories

### US-001: Implement Performance Metrics Display

**Description:** As a trader, I need to see detailed performance statistics.

**Acceptance Criteria:**
- [ ] Update `PerformanceMetrics.tsx` to use real API data
- [ ] Display total trades count
- [ ] Display winning/losing trade counts
- [ ] Display win rate percentage
- [ ] Display average win amount
- [ ] Display average loss amount
- [ ] Display profit factor
- [ ] Display Sharpe ratio
- [ ] Display max drawdown
- [ ] Display average trade duration
- [ ] Add auto-refresh every 10 seconds
- [ ] Typecheck passes
- [ ] Verify in browser that metrics display correctly

**Priority:** 1

### US-002: Implement Equity Curve Chart

**Description:** As a trader, I need to see my equity growth over time.

**Acceptance Criteria:**
- [ ] Update `EquityChart.tsx` to use real API data
- [ ] Display line chart with date on X-axis
- [ ] Display equity value on Y-axis
- [ ] Show balance as secondary line
- [ ] Add date range selector (7d, 30d, 90d, all)
- [ ] Show tooltips with details on hover
- [ ] Highlight all-time high
- [ ] Show drawdown periods
- [ ] Add zoom/pan functionality
- [ ] Typecheck passes
- [ ] Verify in browser that chart displays correctly

**Priority:** 2

### US-003: Implement P&L History Chart

**Description:** As a trader, I need to see my daily/weekly P&L.

**Acceptance Criteria:**
- [ ] Update `PnLChart.tsx` to use real API data
- [ ] Display bar chart showing P&L by period
- [ ] Allow grouping by day, week, or month
- [ ] Color-code (green=profit, red=loss)
- [ ] Show cumulative P&L line
- [ ] Add date range selector
- [ ] Show tooltips with details on hover
- [ ] Typecheck passes
- [ ] Verify in browser that chart displays correctly

**Priority:** 3

## API Endpoints Required

- `GET /performance/metrics` - Performance metrics
- `GET /portfolio/equity-history?days=30` - Equity curve
- `GET /portfolio/pnl-history?grouping=daily` - P&L history

## Success Metrics

- Charts load within 1 second
- Metrics update within 5 seconds
- All time periods display correctly
