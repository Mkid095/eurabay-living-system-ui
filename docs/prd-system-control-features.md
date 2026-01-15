# PRD: System Control Features

## Overview

This PRD implements the system control functionality that allows users to start/stop the trading system, adjust risk parameters, and manage configuration settings.

## Goals

- Implement system start/stop controls
- Add risk parameter adjustments
- Implement configuration management
- Add system status monitoring
- Provide manual override functionality

## User Stories

### US-001: Implement System Start/Stop Controls

**Description:** As an admin, I need to start and stop the trading system.

**Acceptance Criteria:**
- [ ] Update `SystemControls.tsx` to use real API
- [ ] Add "Start System" button when stopped
- [ ] Add "Stop System" button when running
- [ ] Show current system status (running/stopped)
- [ ] Add confirmation dialog for stop action
- [ ] Show loading state during transition
- [ ] Update status in real-time
- [ ] Disable controls when system state is changing
- [ ] Require trader role or higher
- [ ] Typecheck passes
- [ ] Verify in browser that controls work correctly

**Priority:** 1

### US-002: Implement Risk Parameter Controls

**Description:** As an admin, I need to adjust risk management parameters.

**Acceptance Criteria:**
- [ ] Update `RiskParameters.tsx` to use real API
- [ ] Add slider/input for risk per trade (0-100%)
- [ ] Add slider/input for max drawdown (0-100%)
- [ ] Add slider/input for max total open trades (1-50)
- [ ] Display current values
- [ ] Add "Save Changes" button
- [ ] Add "Reset to Defaults" button
- [ ] Validate input ranges
- [ ] Show success/error notifications
- [ ] Require admin role
- [ ] Typecheck passes
- [ ] Verify in browser that controls work correctly

**Priority:** 2

### US-003: Implement Manual Override

**Description:** As an admin, I need to enable manual override to stop automatic trading.

**Acceptance Criteria:**
- [ ] Add "Enable Manual Override" toggle
- [ ] Show warning when manual override is active
- [ ] Disable automatic trading when override is active
- [ ] Allow manual trade entry when override is active
- [ ] Require admin role
- [ ] Typecheck passes
- [ ] Verify in browser that override works correctly

**Priority:** 3

## API Endpoints Required

- `POST /system/start` - Start system
- `POST /system/stop` - Stop system
- `GET /config` - Get configuration
- `PUT /config` - Update configuration
- `POST /system/override` - Toggle manual override

## Success Metrics

- System start/stop success rate > 99%
- Parameter update latency < 1 second
- Manual override response time < 500ms
