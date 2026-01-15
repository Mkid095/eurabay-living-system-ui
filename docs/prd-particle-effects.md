# PRD: Particle Effects System

## Overview

The EURABAY Living System includes libraries for advanced particle effects. This PRD documents the implementation of particle-based visualizations for data displays, trading activity indicators, and ambient effects.

## Goals

- Implement particle effects for data visualization
- Create ambient background particles
- Show trading activity with particle bursts
- Display market volatility with particle intensity
- Add interactive particle systems
- Optimize particle performance

## Current State

**Libraries Installed:**
- `@tsparticles/engine` - Core particle engine
- `@tsparticles/react` - React integration
- `@tsparticles/slim` - Lightweight particle bundle

**Problem:**
- No particle components implemented
- Particle features not integrated
- Libraries installed but unused

## User Stories

### US-001: Create Ambient Particle Background

**Description:** As a user, I need an ambient particle background for visual appeal.

**Acceptance Criteria:**
- [ ] Create `src/components/effects/ParticleBackground.tsx`
- [ ] Initialize tsparticles with config
- [ ] Use lightweight preset for performance
- [ ] Floating particles with slow movement
- [ ] Mouse interaction (repel/attract)
- [ ] Responsive to screen size
- [ ] Disable in low-performance mode
- [ ] Support theme colors
- [ ] Typecheck passes
- [ ] Verify particles render smoothly

**Priority:** 3

**Technical Implementation:**

```typescript
// src/components/effects/ParticleBackground.tsx
'use client';

import { useCallback, useMemo } from 'react';
import Particles from '@tsparticles/react';
import { type Container, type ISourceOptions } from '@tsparticles/engine';

export function ParticleBackground() {
  const options: ISourceOptions = useMemo(() => ({
    background: {
      color: 'transparent',
    },
    fpsLimit: 60,
    particles: {
      color: {
        value: '#c4f54d',
      },
      links: {
        color: '#c4f54d',
        distance: 150,
        enable: true,
        opacity: 0.2,
      },
      move: {
        direction: 'none',
        enable: true,
        outModes: {
          default: 'bounce',
        },
        random: false,
        speed: 0.5,
        straight: false,
      },
      number: {
        density: {
          enable: true,
        },
        value: 50,
      },
      opacity: {
        value: 0.3,
      },
      shape: {
        type: 'circle',
      },
      size: {
        value: { min: 1, max: 3 },
      },
    },
    detectRetina: true,
  }), []);

  const particlesInit = useCallback(async (engine: Awaited<Container>) => {
    // Load slim bundle for performance
  }, []);

  return (
    <Particles
      id="tsparticles"
      init={particlesInit}
      options={options}
      className="absolute inset-0 pointer-events-none"
    />
  );
}
```

### US-002: Create Trade Execution Particles

**Description:** As a trader, I need visual feedback when trades execute.

**Acceptance Criteria:**
- [ ] Create particle burst on trade execution
- [ ] Color-code by trade direction (buy=green, sell=red)
- [ ] Size proportional to trade volume
- [ ] Animate from position outward
- [ ] Fade out over 2 seconds
- [ ] Support multiple concurrent bursts
- [ ] Play sound on burst (optional)
- [ ] Typecheck passes
- [ ] Verify bursts appear correctly

**Priority:** 2

### US-003: Create Market Volatility Particles

**Description:** As a trader, I need to see market volatility through particle intensity.

**Acceptance Criteria:**
- [ ] Create volatility indicator particles
- [ ] Particle count based on volatility level
- [ ] Particle speed based on market activity
- [ ] Color changes with trend (green=bullish, red=bearish)
- [ ] V10: Few, slow particles
- [ ] V100: Many, fast particles
- [ ] Update in real-time with market data
- [ ] Typecheck passes
- [ ] Verify particles reflect volatility

**Priority:** 3

### US-004: Create Evolution Event Particles

**Description:** As a user, I need visual feedback during evolution cycles.

**Acceptance Criteria:**
- [ ] Create particle effect on evolution cycle start
- [ ] DNA-like particle spiral animation
- [ ] Color changes by generation (blue→green→gold)
- [ ] Particle stream representing features mutating
- [ ] Burst effect on cycle completion
- [ ] Show feature success with particle color
- [ ] Smooth transitions between states
- [ ] Typecheck passes
- [ ] Verify animations are smooth

**Priority:** 4

### US-005: Create Performance Celebration Particles

**Description:** As a trader, I need celebratory effects on achievements.

**Acceptance Criteria:**
- [ ] Create confetti burst on significant wins
- [ ] Trigger on milestone achievements
- [ ] Multiple particle types (confetti, stars, sparks)
- [ ] Customizable celebration thresholds
- [ ] Can be disabled in settings
- [ ] Typecheck passes
- [ ] Verify celebrations appear appropriately

**Priority:** 5

## Performance Considerations

### Optimization Strategies
- Limit particle count on mobile devices
- Use canvas rendering (not DOM)
- Implement object pooling
- Throttle particle updates
- Use requestAnimationFrame
- Lazy load particle system
- Disable in low-power mode

### Performance Budget
- Ambient background: < 5% CPU
- Trade bursts: < 10ms per burst
- Market particles: < 2% CPU per market
- Evolution effects: < 15% CPU during cycle
- Target 60 FPS on all devices

## Configuration

### Particle Presets

```typescript
// Ambient preset (background)
const ambientPreset = {
  count: 50,
  speed: 0.5,
  size: { min: 1, max: 3 },
  opacity: 0.3,
};

// Trade burst preset
const tradeBurstPreset = {
  count: 100,
  speed: 3,
  size: { min: 2, max: 6 },
  opacity: 0.8,
  lifetime: 2000,
};

// Volatility preset
const volatilityPresets = {
  V10: { count: 20, speed: 1 },
  V25: { count: 40, speed: 2 },
  V50: { count: 60, speed: 3 },
  V75: { count: 80, speed: 4 },
  V100: { count: 100, speed: 5 },
};
```

## Non-Goals

- No physics-based particles
- No particle collisions
- No 3D particle systems
- No custom particle editors

## Success Metrics

- Particle effects maintain 60 FPS
- No performance degradation on mobile
- < 10MB memory usage for particles
- Smooth animations (no jank)
- User satisfaction > 4/5

## Implementation Order

1. US-001: Create Ambient Particle Background
2. US-002: Create Trade Execution Particles
3. US-003: Create Market Volatility Particles
4. US-004: Create Evolution Event Particles
5. US-005: Create Performance Celebration Particles

## Related PRDs

- PRD: Trading System Features (trade execution events)
- PRD: Market Data Features (volatility data)
- PRD: Evolution System Features (evolution events)
- PRD: Analytics & Performance Features (achievements)
