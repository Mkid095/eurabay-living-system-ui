# PRD: 3D Visualization & Globe Features

## Overview

The EURABAY Living System includes libraries for advanced 3D visualizations including interactive globe displays. This PRD documents the implementation of 3D features for visualizing global trading activity and market data.

## Goals

- Implement interactive 3D globe visualization
- Display global trading activity on globe
- Show market regions with real-time data
- Enable user interaction (rotate, zoom, click)
- Display trade execution locations
- Visualize system metrics in 3D space

## Current State

**Libraries Installed:**
- `three.js` - Core 3D rendering library
- `@react-three/fiber` - React renderer for Three.js
- `@react-three/drei` - Helper components for R3F
- `three-globe` - Specialized globe component
- `cobe` - Code globe for tech displays

**Problem:**
- No 3D components implemented
- Globe visualization not created
- 3D features not integrated into dashboard
- Libraries installed but unused

## User Stories

### US-001: Create 3D Globe Component

**Description:** As a trader, I need to see global trading activity on an interactive 3D globe.

**Acceptance Criteria:**
- [ ] Create `src/components/visualization/TradingGlobe.tsx`
- [ ] Display interactive 3D globe using React Three Fiber
- [ ] Show trade execution locations with markers
- [ ] Support globe rotation and zoom
- [ ] Display market regions (Asia, Europe, Americas)
- [ ] Show real-time trade animations
- [ ] Include legend for market regions
- [ ] Support click on regions for details
- [ ] Handle window resize
- [ ] Optimize for performance (60 FPS)
- [ ] Typecheck passes
- [ ] Verify in browser that globe renders correctly

**Priority:** 2

**Technical Implementation:**

```typescript
// src/components/visualization/TradingGlobe.tsx
'use client';

import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import Globe from 'three-globe';
import { useMemo, useRef, useEffect } from 'react';

interface TradingGlobeProps {
  trades: Trade[];
  marketData: MarketData[];
}

export function TradingGlobe({ trades, marketData }: TradingGlobeProps) {
  const globeRef = useRef<Globe>();

  const globeData = useMemo(() => {
    return trades.map(trade => ({
      lat: getLatForSymbol(trade.symbol),
      lng: getLngForSymbol(trade.symbol),
      size: Math.abs(trade.pnl) / 100,
      color: trade.pnl >= 0 ? '#66bb6a' : '#ef5350',
    }));
  }, [trades]);

  useEffect(() => {
    if (globeRef.current) {
      globeRef.current
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
        .pointsData(globeData)
        .pointAltitude(0.02)
        .pointColor('color');
    }
  }, [globeData]);

  return (
    <div className="w-full h-96 relative">
      <Canvas camera={{ position: [0, 0, 2] }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <Stars />
        <Globe ref={globeRef} />
        <OrbitControls enableZoom={true} enablePan={true} autoRotate={true} />
      </Canvas>
    </div>
  );
}
```

### US-002: Implement Trade Path Visualization

**Description:** As a trader, I need to see trade execution paths on the globe.

**Acceptance Criteria:**
- [ ] Create animated arc paths between locations
- [ ] Show trade origin and destination
- [ ] Display trade volume along path
- [ ] Color-code by profit/loss
- [ ] Animate path drawing
- [ ] Fade out old paths
- [ ] Support path filtering
- [ ] Typecheck passes
- [ ] Verify paths animate correctly

**Priority:** 3

### US-003: Create Market Region Indicators

**Description:** As a trader, I need to see which market regions are active.

**Acceptance Criteria:**
- [ ] Create region markers for V10, V25, V50, V75, V100
- [ ] Display region status (active/inactive)
- [ ] Show volume indicators
- [ ] Color-code by volatility level
- [ ] Pulse animation for active regions
- [ ] Tooltip on hover with details
- [ ] Typecheck passes
- [ ] Verify regions display correctly

**Priority:** 3

### US-004: Add 3D Performance Metrics

**Description:** As an admin, I need to see system performance in 3D space.

**Acceptance Criteria:**
- [ ] Create 3D bar chart for performance metrics
- [ ] Display equity growth as 3D surface
- [ ] Show generation progression as 3D timeline
- [ ] Interactive 3D data exploration
- [ ] Support multiple visualization modes
- [ ] Export 3D scenes as images
- [ ] Typecheck passes
- [ ] Verify 3D charts render correctly

**Priority:** 4

### US-005: Implement Interactive 3D Charts

**Description:** As a trader, I need to explore data in 3D space.

**Acceptance Criteria:**
- [ ] Create 3D scatter plot for feature analysis
- [ ] Create 3D surface plot for optimization
- [ ] Support rotation, zoom, pan
- [ ] Interactive tooltips
- [ ] Click to drill down
- [ ] Synchronized with 2D charts
- [ ] Typecheck passes
- [ ] Verify interactions work

**Priority:** 5

## Technical Considerations

### Performance Optimization
- Use React Three Fiber for efficient rendering
- Implement level-of-detail (LOD) for large datasets
- Use instanced rendering for many points
- Optimize geometry and materials
- Limit particle counts

### Browser Compatibility
- WebGL support required
- Fallback for unsupported browsers
- Progressive enhancement
- Mobile performance considerations

### Data Requirements
- Coordinates for trade locations
- Real-time trade data feeds
- Market region definitions
- Historical data for time-based visualizations

## Non-Goals

- No VR/AR support in this phase
- No 3D model importing
- No custom shader development
- No physics simulation

## Success Metrics

- Globe renders at 60 FPS
- Supports 1000+ simultaneous trade markers
- Interaction latency < 100ms
- Zero memory leaks
- Mobile compatible

## Implementation Order

1. US-001: Create 3D Globe Component
2. US-003: Create Market Region Indicators
3. US-002: Implement Trade Path Visualization
4. US-005: Implement Interactive 3D Charts
5. US-004: Add 3D Performance Metrics

## Related PRDs

- PRD: Trading System Features (trade data for visualization)
- PRD: Analytics & Performance Features (metrics for 3D display)
- PRD: Market Data Features (region information)
