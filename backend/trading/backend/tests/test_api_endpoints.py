"""
Tests for active trade management API endpoints.

This module tests all REST API endpoints as specified in US-011.
"""

import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.app import app
from backend.api.routes import trade_manager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def setup_mock_data():
    """Set up mock trade data for testing."""
    # Add some mock positions
    trade_manager._positions = {
        12345: {
            "ticket": 12345,
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0850,
            "current_price": 1.0880,
            "volume": 0.1,
            "stop_loss": 1.0800,
            "take_profit": 1.0900,
            "entry_time": datetime.now(),
            "profit": 30.0,
            "swap": 0.5,
            "commission": -2.0,
            "state": "open",
            "trade_age_seconds": 3600.0,
        },
        12346: {
            "ticket": 12346,
            "symbol": "GBPUSD",
            "direction": "SELL",
            "entry_price": 1.2650,
            "current_price": 1.2630,
            "volume": 0.1,
            "stop_loss": 1.2700,
            "take_profit": 1.2600,
            "entry_time": datetime.now(),
            "profit": 20.0,
            "swap": -0.2,
            "commission": -2.0,
            "state": "breakeven",
            "trade_age_seconds": 1800.0,
        },
    }
    trade_manager._paused.clear()
    yield
    # Cleanup
    trade_manager._positions.clear()
    trade_manager._paused.clear()


class TestGetActiveTrades:
    """Tests for GET /api/trades/active endpoint."""

    def test_get_active_trades_success(self, client, setup_mock_data):
        """Test successfully fetching active trades."""
        response = client.get("/api/trades/active")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["ticket"] == 12345
        assert data[0]["symbol"] == "EURUSD"
        assert data[0]["direction"] == "BUY"

    def test_get_active_trades_empty(self, client):
        """Test fetching active trades when none exist."""
        trade_manager._positions.clear()
        response = client.get("/api/trades/active")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetTradeState:
    """Tests for GET /api/trades/{ticket}/state endpoint."""

    def test_get_trade_state_success(self, client, setup_mock_data):
        """Test successfully fetching trade state."""
        response = client.get("/api/trades/12345/state")
        assert response.status_code == 200
        data = response.json()
        assert data["ticket"] == 12345
        assert data["current_state"] == "open"
        assert "state_history" in data
        assert isinstance(data["state_history"], list)

    def test_get_trade_state_not_found(self, client):
        """Test fetching state for non-existent trade."""
        response = client.get("/api/trades/99999/state")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestCloseTrade:
    """Tests for POST /api/trades/{ticket}/close endpoint."""

    def test_close_trade_success(self, client, setup_mock_data):
        """Test successfully closing a trade."""
        request_data = {
            "reason": "Manual close - target reached",
            "user": "test_user",
        }
        response = client.post("/api/trades/12345/close", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ticket"] == 12345
        assert data["action"] == "close"
        assert "timestamp" in data

    def test_close_trade_not_found(self, client):
        """Test closing non-existent trade."""
        request_data = {
            "reason": "Test close",
            "user": "test_user",
        }
        response = client.post("/api/trades/99999/close", json=request_data)
        assert response.status_code == 404


class TestPauseManagement:
    """Tests for POST /api/trades/{ticket}/pause endpoint."""

    def test_pause_management_success(self, client, setup_mock_data):
        """Test successfully pausing management."""
        request_data = {
            "reason": "News event approaching",
            "user": "test_user",
        }
        response = client.post("/api/trades/12345/pause", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "pause"
        assert 12345 in trade_manager._paused

    def test_pause_management_not_found(self, client):
        """Test pausing management for non-existent trade."""
        request_data = {
            "reason": "Test pause",
            "user": "test_user",
        }
        response = client.post("/api/trades/99999/pause", json=request_data)
        assert response.status_code == 404


class TestResumeManagement:
    """Tests for POST /api/trades/{ticket}/resume endpoint."""

    def test_resume_management_success(self, client, setup_mock_data):
        """Test successfully resuming management."""
        # First pause
        trade_manager._paused.add(12345)

        request_data = {
            "reason": "News event passed",
            "user": "test_user",
        }
        response = client.post("/api/trades/12345/resume", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "resume"
        assert 12345 not in trade_manager._paused

    def test_resume_management_not_found(self, client):
        """Test resuming management for non-existent trade."""
        request_data = {
            "reason": "Test resume",
            "user": "test_user",
        }
        response = client.post("/api/trades/99999/resume", json=request_data)
        assert response.status_code == 404


class TestSetStopLoss:
    """Tests for PUT /api/trades/{ticket}/sl endpoint."""

    def test_set_stop_loss_success(self, client, setup_mock_data):
        """Test successfully setting stop loss."""
        request_data = {
            "stop_loss": 1.0820,
            "reason": "Locking in partial profit",
            "user": "test_user",
        }
        response = client.put("/api/trades/12345/sl", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "set_stop_loss"
        assert trade_manager._positions[12345]["stop_loss"] == 1.0820

    def test_set_stop_loss_not_found(self, client):
        """Test setting stop loss for non-existent trade."""
        request_data = {
            "stop_loss": 1.0800,
            "reason": "Test",
            "user": "test_user",
        }
        response = client.put("/api/trades/99999/sl", json=request_data)
        assert response.status_code == 404

    def test_set_stop_loss_invalid_value(self, client):
        """Test setting stop loss with invalid value."""
        request_data = {
            "stop_loss": -1.0,  # Invalid: negative value
            "reason": "Test",
            "user": "test_user",
        }
        response = client.put("/api/trades/12345/sl", json=request_data)
        # Should return validation error (422)
        assert response.status_code == 422


class TestSetTakeProfit:
    """Tests for PUT /api/trades/{ticket}/tp endpoint."""

    def test_set_take_profit_success(self, client, setup_mock_data):
        """Test successfully setting take profit."""
        request_data = {
            "take_profit": 1.0920,
            "reason": "Extending target",
            "user": "test_user",
        }
        response = client.put("/api/trades/12345/tp", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "set_take_profit"
        assert trade_manager._positions[12345]["take_profit"] == 1.0920

    def test_set_take_profit_not_found(self, client):
        """Test setting take profit for non-existent trade."""
        request_data = {
            "take_profit": 1.0900,
            "reason": "Test",
            "user": "test_user",
        }
        response = client.put("/api/trades/99999/tp", json=request_data)
        assert response.status_code == 404

    def test_set_take_profit_invalid_value(self, client):
        """Test setting take profit with invalid value."""
        request_data = {
            "take_profit": 0.0,  # Invalid: zero value
            "reason": "Test",
            "user": "test_user",
        }
        response = client.put("/api/trades/12345/tp", json=request_data)
        # Should return validation error (422)
        assert response.status_code == 422


class TestGetPerformanceMetrics:
    """Tests for GET /api/trades/performance endpoint."""

    def test_get_performance_metrics_success(self, client):
        """Test successfully fetching performance metrics."""
        response = client.get("/api/trades/performance")
        assert response.status_code == 200
        data = response.json()
        assert "actively_managed_win_rate" in data
        assert "set_and_forget_win_rate" in data
        assert "improvement_percentage" in data
        assert "trailing_stop_savings" in data
        assert "breakeven_preventions" in data
        assert data["actively_managed_win_rate"] > 0
        assert data["improvement_percentage"] > 0


class TestWebsocket:
    """Tests for WebSocket endpoint."""

    def test_websocket_connection(self, client):
        """Test WebSocket connection and initial message."""
        with client.websocket_connect("/api/trades/ws/trades") as websocket:
            data = websocket.receive_json()
            assert data["event_type"] == "connected"
            assert "timestamp" in data

    def test_websocket_disconnect(self, client):
        """Test WebSocket disconnection."""
        with client.websocket_connect("/api/trades/ws/trades") as websocket:
            # Just connect and disconnect
            pass
        # Should disconnect cleanly


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "EURABAY Active Trade Management API"
        assert data["status"] == "operational"
        assert "endpoints" in data


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
