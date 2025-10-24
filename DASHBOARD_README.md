# EURABAY Living System v5.0 - Dashboard Implementation

## 🎯 Overview

This dashboard provides a comprehensive real-time monitoring and control interface for the EURABAY Living System v5.0, a sophisticated algorithmic trading system that trades Deriv.com volatility indices (V10, V25, V50, V75, V100) with evolutionary adaptation capabilities.

## ✨ Key Features Implemented

### 1. **Dashboard Section**
- **Portfolio Metrics**: Real-time portfolio value, P&L, active trades, and win rate
- **Evolution Status**: Current generation, controller decision, and system cycles
- **Generation History Chart**: Visual tracking of evolution progression over time
- **Equity & P&L Charts**: Interactive charts showing portfolio performance
- **Active Trades Overview**: Quick view of current positions
- **Deriv Market Overview**: Real-time data for all 5 volatility indices

### 2. **Trading Section**
- **Enhanced Active Trades Table**: Detailed trade information including:
  - Entry/current prices and P&L
  - HTF (H1) and LTF (M1) context
  - Evolved features used in each trade
  - Confidence levels
- **Pending Signals Queue**: Signals awaiting portfolio approval
- **Recent Trades History**: Closed trades with outcomes
- **Execution Log**: Real-time feed of trade executions and events

### 3. **Analytics Section**
- **Performance Metrics**: Total trades, win rate, Sharpe ratio, max drawdown
- **Equity & P&L History**: Long-term performance visualization
- **Feature Success Chart**: Success rates of evolved features
- **Mutation Success Chart**: Effectiveness of different mutation types
- **Controller Decision Timeline**: Evolution strategy decisions over time
- **Generation History**: Complete evolution progression tracking

### 4. **Evolution Section** (NEW)
Complete transparency into the Living System's evolutionary process:
- **Evolution Metrics Card**: Current generation, controller decision, cycles completed
- **Generation History Chart**: Track fitness and performance improvements
- **Feature Success Analysis**: Which evolved features are performing best
- **Mutation Success Breakdown**: Which mutation strategies are most effective
- **Controller Decision Timeline**: Historical evolution decisions with reasoning
- **Evolution Event Logs**: Real-time feed of evolution events
- **Enhanced Trades View**: See which features contributed to each trade

### 5. **Configuration Section**
- **System Controls**: Start/stop processing, manual overrides
- **Risk Parameters**: Adjustable risk management settings
- **Evolution Parameters** (NEW): Fine-tune evolution behavior
  - Mutation rate
  - Adaptive min accuracy threshold
  - Performance threshold for triggering evolution
  - Evolution aggression level
- **Deriv Markets Status**: Monitor all volatility indices
- **Logs Viewer**: Searchable system logs

## 🏗️ Architecture

### Component Structure
```
src/
├── app/
│   └── page.tsx                          # Main dashboard page
├── components/
│   ├── dashboard/
│   │   ├── ActiveTradesTable.tsx         # Basic trades table
│   │   ├── EnhancedActiveTradesTable.tsx # Trades with evolution context
│   │   ├── ControllerDecisionTimeline.tsx # Controller decisions
│   │   ├── DerivMarketOverview.tsx       # Deriv markets widget
│   │   ├── EquityChart.tsx               # Portfolio equity chart
│   │   ├── EvolutionLogViewer.tsx        # Evolution events feed
│   │   ├── EvolutionMetrics.tsx          # Evolution status card
│   │   ├── EvolutionParameters.tsx       # Evolution config controls
│   │   ├── ExecutionLog.tsx              # Trade execution log
│   │   ├── FeatureSuccessChart.tsx       # Feature performance chart
│   │   ├── GenerationHistoryChart.tsx    # Evolution history chart
│   │   ├── Header.tsx                    # Dashboard header
│   │   ├── LogsViewer.tsx                # System logs viewer
│   │   ├── MarketOverview.tsx            # Market data widget
│   │   ├── MetricCard.tsx                # Metric display card
│   │   ├── MutationSuccessChart.tsx      # Mutation success chart
│   │   ├── PendingSignals.tsx            # Pending signals queue
│   │   ├── PerformanceMetrics.tsx        # Performance stats
│   │   ├── PnLChart.tsx                  # P&L history chart
│   │   ├── RecentTrades.tsx              # Recent trades list
│   │   ├── RiskParameters.tsx            # Risk config controls
│   │   ├── Sidebar.tsx                   # Navigation sidebar
│   │   └── SystemControls.tsx            # System control buttons
│   └── ui/                               # Shadcn UI components
├── hooks/
│   ├── useDashboardData.ts               # Dashboard data hook
│   └── useEvolutionData.ts               # Evolution data hook
├── types/
│   └── evolution.ts                      # Evolution type definitions
└── lib/
    └── utils.ts                          # Utility functions
```

### Data Flow
```
Backend API → Custom Hooks → React Components → UI Display
     ↓
WebSocket → Real-time Updates → State Updates → Re-render
```

## 🎨 Design System

### Color Palette (Dark Green/Lime Theme)
```css
Primary:    #c4f54d (Lime green)
Background: #1a2f2f (Dark green)
Card:       #233d3d (Medium dark green)
Profit:     #66bb6a (Green)
Loss:       #ef5350 (Red)
Warning:    #ffa726 (Orange)
Info:       #29b6f6 (Blue)
```

### Typography
- **Font Family**: Inter (Google Fonts)
- **Headers**: 600-800 weight
- **Body**: 400-500 weight
- **Monospace**: For prices and technical data

### Responsive Breakpoints
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

## 🔌 Backend Integration

### Required API Endpoints

See **[API_INTEGRATION.md](./API_INTEGRATION.md)** for complete API documentation including:
- System status and health endpoints
- Evolution metrics and history
- Market data feeds
- Trading activity endpoints
- Portfolio and performance data
- Configuration management
- WebSocket event specifications

### Mock Data vs Live Data

Currently, the dashboard uses **mock data** provided by custom hooks:
- `useDashboardData.ts`: Portfolio, trades, charts
- `useEvolutionData.ts`: Evolution metrics, feature success, mutations

To connect to your Python backend:

1. **Update hook implementations** to fetch from your API:
```typescript
// Example: useEvolutionData.ts
useEffect(() => {
  const fetchData = async () => {
    const response = await fetch('/api/evolution/metrics');
    const data = await response.json();
    setEvolutionMetrics(data);
  };
  
  fetchData();
  const interval = setInterval(fetchData, 5000);
  return () => clearInterval(interval);
}, []);
```

2. **Implement WebSocket connection** for real-time updates:
```typescript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const { event: eventType, data } = JSON.parse(event.data);
  // Update state based on event type
};
```

3. **Add API client** using fetch or axios:
```typescript
// src/lib/api.ts
export const api = {
  getEvolutionMetrics: () => fetch('/api/evolution/metrics').then(r => r.json()),
  getActiveTrades: () => fetch('/api/trades/active').then(r => r.json()),
  // ... more endpoints
};
```

## 📊 Evolution Tracking Features

### What Makes This a "Living System"

The dashboard provides complete transparency into the system's evolutionary process:

1. **Generation Tracking**: See how the system evolves over time
2. **Controller Decisions**: Understand why evolution was triggered
3. **Feature Success Analysis**: Know which evolved features work best
4. **Mutation Effectiveness**: Track which mutation strategies succeed
5. **Trade Attribution**: See exactly which features contributed to each trade
6. **Real-time Evolution Logs**: Monitor evolution events as they happen

### Key Metrics Displayed

- **Current Generation**: Which iteration of the feature set is running
- **Controller Decision**: STABLE | EVOLVE_CONSERVATIVE | EVOLVE_MODERATE | EVOLVE_AGGRESSIVE
- **Cycles Completed**: Total system processing cycles
- **Feature Success Rates**: Win/loss ratio per evolved feature
- **Mutation Success Rates**: Effectiveness of different mutation types
- **Fitness Progression**: How system performance improves over generations

## 🚀 Getting Started

### Installation

```bash
# Install dependencies
npm install

# or with bun
bun install
```

### Development

```bash
# Run development server
npm run dev

# or with bun
bun dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
npm run start
```

## 📱 Responsive Design

The dashboard is fully responsive with **mobile-first design**:

- **Mobile (< 640px)**: 
  - Collapsible sidebar
  - Stacked metric cards
  - Simplified tables
  - Touch-friendly controls

- **Tablet (640px - 1024px)**:
  - 2-column layouts
  - Larger touch targets
  - Optimized chart sizes

- **Desktop (> 1024px)**:
  - Fixed sidebar
  - Multi-column grids
  - Full-featured tables
  - Large interactive charts

## 🎯 Trading Markets

The system trades **Deriv.com Volatility Indices**:

- **V10**: Volatility 10 Index (10% annual volatility)
- **V25**: Volatility 25 Index (25% annual volatility)
- **V50**: Volatility 50 Index (50% annual volatility)
- **V75**: Volatility 75 Index (75% annual volatility)
- **V100**: Volatility 100 Index (100% annual volatility)

All markets trade **24/7** with **synthetic pricing** that follows real market dynamics.

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### System Configuration

Adjustable via the Config section:
- Risk per trade (% of portfolio)
- Max drawdown threshold
- Max simultaneous open trades
- Evolution parameters (mutation rates, thresholds)
- Market symbols to trade
- Timeframes (LTF/HTF)

## 📈 Chart Libraries

The dashboard uses **Recharts** for all visualizations:
- Line charts (equity, generation history)
- Bar charts (feature success)
- Pie charts (mutation breakdown)
- Area charts (P&L)

Charts are fully responsive and themed to match the design system.

## 🔐 Security Considerations

When deploying to production:

1. **Add authentication**: Protect all routes with authentication
2. **Secure WebSocket**: Use WSS (WebSocket Secure)
3. **API authentication**: Include bearer tokens in API requests
4. **Rate limiting**: Implement on backend
5. **Input validation**: Validate all user inputs
6. **HTTPS only**: Never deploy without SSL/TLS

## 🐛 Troubleshooting

### Charts not displaying
- Ensure `recharts` is installed
- Check browser console for errors
- Verify data format matches expected schema

### WebSocket not connecting
- Check WebSocket URL in environment variables
- Ensure backend WebSocket server is running
- Check browser console for connection errors

### Data not updating
- Verify API endpoints are accessible
- Check network tab in browser dev tools
- Ensure backend is returning correct data format

## 📝 TODO / Future Enhancements

- [ ] Add authentication/authorization
- [ ] Implement data export (CSV/JSON)
- [ ] Add custom date range selectors
- [ ] Implement trade filtering/search
- [ ] Add performance comparison tools
- [ ] Create custom alert rules
- [ ] Add dark/light mode toggle (currently dark only)
- [ ] Implement trade replay functionality
- [ ] Add multi-user support
- [ ] Create mobile app version

## 🤝 Backend Integration Checklist

- [ ] Implement all API endpoints from API_INTEGRATION.md
- [ ] Set up WebSocket server for real-time updates
- [ ] Add authentication middleware
- [ ] Configure CORS for frontend origin
- [ ] Implement rate limiting
- [ ] Set up logging and monitoring
- [ ] Test all endpoints with frontend
- [ ] Document any custom endpoints
- [ ] Implement error handling
- [ ] Set up database connections for historical data

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Shadcn UI](https://ui.shadcn.com/)
- [Recharts](https://recharts.org/)
- [Deriv API Documentation](https://api.deriv.com/)

## 📄 License

[Add your license here]

## 👥 Contributors

[Add contributors here]

---

**Note**: This dashboard is the frontend interface only. It requires the EURABAY Living System v5.0 Python backend to be running for full functionality. See API_INTEGRATION.md for complete backend requirements.
