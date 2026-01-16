# EURABAY Active Trade Management Backend

Python backend for active trade management with trailing stops, partial profits, breakeven mechanisms, and holding time optimization.

## Installation

```bash
cd backend/trading
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_active_trade_manager.py -v
```

## Project Structure

```
backend/trading/
├── backend/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── active_trade_manager.py  # Main trade manager
│   │   ├── trade_state.py           # State machine
│   │   └── trade_position.py        # Position model
│   ├── managers/                    # Management managers (future stories)
│   ├── models/                      # Data models
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_active_trade_manager.py
│   └── utils/                       # Utilities
└── pyproject.toml
```

## Current Implementation

### Story US-001: Active Trade Manager Foundation

The foundation includes:

- **ActiveTradeManager**: Core class for monitoring open positions
  - `monitor_open_trades()`: Main monitoring loop (5 second interval)
  - `fetch_open_positions()`: Fetch positions from MT5
  - `calculate_current_pnl()`: Calculate PnL for each position
  - `get_trade_age()`: Get time since entry
  - `get_trade_state()`: Get current trade state

- **TradeStateMachine**: Manages state transitions
  - States: PENDING, OPEN, PARTIAL, CLOSED
  - Validates state transitions
  - Tracks state history

- **TradePosition**: Data model for positions
  - Position details (ticket, symbol, direction, etc.)
  - PnL tracking
  - State tracking with history

- **Comprehensive logging** for all trade operations

- **Unit tests** covering all core functionality

## Future Stories

- US-002: Trailing stop mechanism
- US-003: Breakeven mechanism
- US-004: Partial profit taking
- US-005: Holding time optimization
- US-006: Scale-in functionality
- US-007: Scale-out functionality
- And more...

## Tech Stack

- Python 3.11+
- Asyncio for monitoring loop
- Comprehensive logging
- Full unit test coverage with pytest
