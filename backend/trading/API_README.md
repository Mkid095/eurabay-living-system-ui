# Active Trade Management API

## Overview

This API provides REST and WebSocket endpoints for controlling and monitoring active trade management in the EURABAY Living System.

## Implementation

This implementation fulfills **US-011: Implement active management API endpoints** from the PRD.

## Tech Stack

- **Framework**: FastAPI 0.128+
- **WebSocket**: Native FastAPI WebSocket support
- **Validation**: Pydantic 2.12+
- **Testing**: Pytest with async support

## Project Structure

```
backend/trading/
├── backend/
│   ├── api/
│   │   ├── __init__.py          # API package initialization
│   │   ├── schemas.py           # Pydantic models for request/response
│   │   ├── routes.py            # All API endpoints
│   │   └── app.py               # FastAPI application
│   └── tests/
│       └── test_api_endpoints.py # Comprehensive API tests
└── pyproject.toml               # Dependencies
```

## API Endpoints

### REST Endpoints

#### Get Active Trades
- **Endpoint**: `GET /api/trades/active`
- **Description**: Retrieve all actively managed trades
- **Response**: List of `TradePositionResponse` objects

#### Get Trade State
- **Endpoint**: `GET /api/trades/{ticket}/state`
- **Description**: Get trade state and complete history
- **Response**: `TradeStateResponse` with state transitions

#### Close Trade
- **Endpoint**: `POST /api/trades/{ticket}/close`
- **Description**: Manually close a position
- **Request Body**:
  ```json
  {
    "reason": "Target reached",
    "user": "trader_name"
  }
  ```

#### Pause Management
- **Endpoint**: `POST /api/trades/{ticket}/pause`
- **Description**: Pause active management for a position
- **Request Body**:
  ```json
  {
    "reason": "News event",
    "user": "trader_name"
  }
  ```

#### Resume Management
- **Endpoint**: `POST /api/trades/{ticket}/resume`
- **Description**: Resume active management for a position
- **Request Body**:
  ```json
  {
    "reason": "News passed",
    "user": "trader_name"
  }
  ```

#### Set Stop Loss
- **Endpoint**: `PUT /api/trades/{ticket}/sl`
- **Description**: Manually set stop loss level
- **Request Body**:
  ```json
  {
    "stop_loss": 1.0850,
    "reason": "Locking profit",
    "user": "trader_name"
  }
  ```

#### Set Take Profit
- **Endpoint**: `PUT /api/trades/{ticket}/tp`
- **Description**: Manually set take profit level
- **Request Body**:
  ```json
  {
    "take_profit": 1.0950,
    "reason": "Extending target",
    "user": "trader_name"
  }
  ```

#### Get Performance Metrics
- **Endpoint**: `GET /api/trades/performance`
- **Description**: Get active vs passive management comparison
- **Response**: `PerformanceMetrics` object

### WebSocket Endpoint

#### Trade Updates Stream
- **Endpoint**: `WS /api/trades/ws/trades`
- **Description**: Real-time trade updates
- **Message Types**:
  - `connected`: Connection established
  - `position_closed`: Position closed
  - `management_paused`: Management paused
  - `management_resumed`: Management resumed
  - `stop_loss_updated`: Stop loss changed
  - `take_profit_updated`: Take profit changed

## Running the API

### Development Server

```bash
cd backend/trading
python -m uvicorn backend.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
cd backend/trading
python -m uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

### Run All Tests

```bash
cd backend/trading
python -m pytest backend/tests/test_api_endpoints.py -v
```

### Run Specific Test Class

```bash
python -m pytest backend/tests/test_api_endpoints.py::TestGetActiveTrades -v
```

### Test Coverage

The test suite includes:
- ✅ 21 comprehensive tests
- ✅ All REST endpoints tested
- ✅ WebSocket connection tested
- ✅ Error cases covered (404, validation errors)
- ✅ Success cases verified
- ✅ Mock data for isolated testing

## API Documentation

Once the server is running, access the interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Health Check

- **Endpoint**: `GET /health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "active-trade-management-api"
  }
  ```

## Features Implemented

✅ **All acceptance criteria from US-011 met**:

1. ✅ GET /api/trades/active - All actively managed trades
2. ✅ GET /api/trades/:id/state - Trade state and history
3. ✅ POST /api/trades/:id/close - Manual close
4. ✅ POST /api/trades/:id/pause - Pause active management
5. ✅ POST /api/trades/:id/resume - Resume active management
6. ✅ PUT /api/trades/:id/sl - Manual stop loss update
7. ✅ PUT /api/trades/:id/tp - Manual take profit update
8. ✅ GET /api/trades/performance - Active vs passive comparison
9. ✅ WebSocket streaming for trade updates
10. ✅ Comprehensive test suite (21 tests, all passing)

## Integration Notes

This API currently uses a mock `TradeManager` for demonstration. In production, it should integrate with:

- `ActiveTradeManager` - For position monitoring
- `ManualOverrideManager` - For manual controls
- `PerformanceComparator` - For metrics calculation
- MT5 connector - For actual trade execution

## Security Considerations

For production deployment:

1. Add authentication/authorization middleware
2. Configure CORS appropriately (currently allows all origins)
3. Add rate limiting
4. Implement HTTPS/TLS
5. Add request signing for sensitive operations
6. Implement audit logging for all manual actions

## Next Steps

Future enhancements could include:

1. Integration with actual MT5 connector
2. Database persistence for trade history
3. Authentication and authorization
4. Rate limiting and throttling
5. Metrics and monitoring
6. API versioning
7. Pagination for large result sets
8. Advanced filtering and search

## Story Status

- **User Story**: US-011
- **Title**: Implement active management API endpoints
- **Status**: ✅ **COMPLETE**
- **Tests**: 21/21 passing
- **PRD Updated**: Yes
