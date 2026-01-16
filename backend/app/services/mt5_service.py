"""
MT5 Service - MetaTrader 5 connection and trading operations.
Handles connection management, data fetching, and order execution.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from loguru import logger
from app.core.config import settings


class MT5Error(Exception):
    """Base exception for MT5 errors."""
    pass


class ConnectionError(MT5Error):
    """Exception raised when MT5 connection fails."""
    pass


class OrderError(MT5Error):
    """Exception raised when order execution fails."""
    pass


class DataError(MT5Error):
    """Exception raised when data retrieval fails."""
    pass


class ConnectionStatus(Enum):
    """MT5 connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class TickData:
    """Tick data structure."""
    symbol: str
    bid: float
    ask: float
    spread: float
    time: datetime
    volume: int


@dataclass
class OHLCVData:
    """OHLCV data structure."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Position:
    """Position data structure."""
    ticket: int
    symbol: str
    type: str  # 'buy' or 'sell'
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    comment: str
    time: datetime


@dataclass
class AccountInfo:
    """Account information structure."""
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    currency: str
    company: str
    server: str


class MT5Service:
    """
    MetaTrader 5 service for connection management and trading operations.

    This service handles:
    - MT5 terminal connection and authentication
    - Automatic reconnection with retry logic
    - Real-time price data fetching
    - Historical OHLCV data retrieval
    - Order placement and management
    - Position monitoring
    - Account information retrieval
    - Comprehensive error handling and logging
    """

    def __init__(self):
        """Initialize MT5 service."""
        if mt5 is None:
            raise ImportError(
                "MetaTrader5 library is not installed. "
                "Install it with: pip install MetaTrader5"
            )

        # Connection settings
        self._account: int = settings.MT5_ACCOUNT
        self._password: str = settings.MT5_PASSWORD
        self._server: str = settings.MT5_SERVER
        self._path: str = settings.MT5_PATH

        # Connection state
        self._status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self._last_connection_attempt: Optional[datetime] = None
        self._connection_lock = asyncio.Lock()

        # Reconnection settings
        self._max_retries: int = 5
        self._retry_delay: int = 5  # seconds
        self._retry_count: int = 0

        # Heartbeat settings
        self._last_heartbeat: Optional[datetime] = None
        self._heartbeat_interval: int = 30  # seconds

        logger.info("MT5Service initialized")

    @property
    def is_connected(self) -> bool:
        """Check if MT5 is connected."""
        return (
            self._status == ConnectionStatus.CONNECTED and
            mt5 is not None and
            mt5.terminal_info() is not None
        )

    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._status

    async def initialize(self) -> bool:
        """
        Initialize MT5 connection with login credentials.

        Returns:
            bool: True if connection successful, False otherwise.

        Raises:
            ConnectionError: If connection fails after retries.
        """
        async with self._connection_lock:
            self._status = ConnectionStatus.CONNECTING
            logger.info(f"Attempting to connect to MT5 terminal (account: {self._account})")

            try:
                # Initialize MT5 terminal
                if not self._initialize_terminal():
                    raise ConnectionError("Failed to initialize MT5 terminal")

                # Login with credentials
                if not self._login():
                    raise ConnectionError("Failed to login to MT5 account")

                # Verify connection
                if not self._verify_connection():
                    raise ConnectionError("Failed to verify MT5 connection")

                self._status = ConnectionStatus.CONNECTED
                self._retry_count = 0
                self._last_heartbeat = datetime.now()
                self._last_connection_attempt = datetime.now()

                logger.success(f"Successfully connected to MT5 (account: {self._account})")
                return True

            except ConnectionError as e:
                self._status = ConnectionStatus.FAILED
                logger.error(f"MT5 connection failed: {e}")
                raise

    def _initialize_terminal(self) -> bool:
        """
        Initialize MT5 terminal.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Initialize MT5 with optional custom path
            if self._path:
                logger.debug(f"Initializing MT5 with custom path: {self._path}")
                initialized = mt5.initialize(path=self._path)
            else:
                logger.debug("Initializing MT5 with default path")
                initialized = mt5.initialize()

            if not initialized:
                error_code = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error_code}")
                return False

            logger.debug("MT5 terminal initialized successfully")
            return True

        except Exception as e:
            logger.exception(f"Exception during MT5 initialization: {e}")
            return False

    def _login(self) -> bool:
        """
        Login to MT5 account.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not self._account or not self._password or not self._server:
                logger.warning(
                    "MT5 credentials not configured. "
                    "Using anonymous connection (limited functionality)."
                )
                return True  # Allow anonymous connection for testing

            logger.debug(
                f"Logging in to MT5: account={self._account}, server={self._server}"
            )

            authorized = mt5.login(
                login=self._account,
                password=self._password,
                server=self._server
            )

            if not authorized:
                error_code = mt5.last_error()
                logger.error(f"MT5 login failed: {error_code}")
                return False

            logger.debug("MT5 login successful")
            return True

        except Exception as e:
            logger.exception(f"Exception during MT5 login: {e}")
            return False

    def _verify_connection(self) -> bool:
        """
        Verify MT5 connection is active.

        Returns:
            bool: True if connected, False otherwise.
        """
        try:
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                logger.error("MT5 terminal_info returned None")
                return False

            connected = terminal_info.trade_allowed
            if not connected:
                logger.warning("MT5 connected but trading not allowed")

            logger.debug("MT5 connection verified")
            return True

        except Exception as e:
            logger.exception(f"Exception during MT5 connection verification: {e}")
            return False

    async def reconnect(self) -> bool:
        """
        Reconnect to MT5 with retry mechanism.

        Returns:
            bool: True if reconnection successful, False otherwise.
        """
        async with self._connection_lock:
            self._status = ConnectionStatus.RECONNECTING
            logger.info(f"Attempting MT5 reconnection (attempt {self._retry_count + 1}/{self._max_retries})")

            # Check if max retries exceeded
            if self._retry_count >= self._max_retries:
                logger.error(f"Max reconnection attempts ({self._max_retries}) exceeded")
                self._status = ConnectionStatus.FAILED
                return False

            # Shutdown existing connection
            self._shutdown()

            # Wait before retry
            await asyncio.sleep(self._retry_delay)

            # Increment retry count
            self._retry_count += 1

            try:
                # Reinitialize
                if not self._initialize_terminal():
                    raise ConnectionError("Failed to reinitialize MT5 terminal")

                # Re-login
                if not self._login():
                    raise ConnectionError("Failed to re-login to MT5 account")

                # Verify connection
                if not self._verify_connection():
                    raise ConnectionError("Failed to verify MT5 reconnection")

                self._status = ConnectionStatus.CONNECTED
                self._retry_count = 0  # Reset retry count on success
                self._last_heartbeat = datetime.now()
                self._last_connection_attempt = datetime.now()

                logger.success(f"MT5 reconnection successful on attempt {self._retry_count}")
                return True

            except ConnectionError as e:
                self._status = ConnectionStatus.FAILED
                logger.error(f"MT5 reconnection failed: {e}")
                return False

    async def check_connection(self, auto_reconnect: bool = False) -> bool:
        """
        Check and maintain MT5 connection.

        Args:
            auto_reconnect: If True, attempt reconnection on failure.

        Returns:
            bool: True if connected, False otherwise.
        """
        # Check if heartbeat is needed
        if self._last_heartbeat:
            time_since_heartbeat = (datetime.now() - self._last_heartbeat).total_seconds()
            if time_since_heartbeat < self._heartbeat_interval:
                return self.is_connected

        # Perform heartbeat check
        if self.is_connected:
            try:
                # Try to get terminal info as heartbeat
                terminal_info = mt5.terminal_info()
                if terminal_info:
                    self._last_heartbeat = datetime.now()
                    return True
                else:
                    logger.warning("MT5 heartbeat failed")
                    if auto_reconnect:
                        return await self.reconnect()
                    return False

            except Exception as e:
                logger.warning(f"MT5 heartbeat exception: {e}")
                if auto_reconnect:
                    return await self.reconnect()
                return False
        else:
            logger.warning("MT5 not connected")
            if auto_reconnect:
                return await self.reconnect()
            return False

    async def get_price(self, symbol: str) -> Optional[TickData]:
        """
        Get current price (tick) data for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'V10', 'V25').

        Returns:
            TickData: Current tick data, or None if unavailable.

        Raises:
            ConnectionError: If MT5 is not connected.
            DataError: If data retrieval fails.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot fetch price - MT5 not connected")

        try:
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                logger.warning(f"No tick data available for {symbol}")
                return None

            tick_data = TickData(
                symbol=symbol,
                bid=tick.bid,
                ask=tick.ask,
                spread=tick.ask - tick.bid,
                time=datetime.fromtimestamp(tick.time),
                volume=tick.volume
            )

            logger.debug(f"Fetched tick data for {symbol}: bid={tick_data.bid:.5f}, ask={tick_data.ask:.5f}")
            return tick_data

        except Exception as e:
            logger.exception(f"Exception fetching price for {symbol}: {e}")
            raise DataError(f"Failed to fetch price for {symbol}: {e}")

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: int = None,
        count: int = 100
    ) -> List[OHLCVData]:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Trading symbol.
            timeframe: MT5 timeframe constant (default: M1).
            count: Number of bars to retrieve.

        Returns:
            List[OHLCVData]: List of OHLCV data.

        Raises:
            ConnectionError: If MT5 is not connected.
            DataError: If data retrieval fails.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot fetch historical data - MT5 not connected")

        # Set default timeframe if not provided
        if timeframe is None:
            timeframe = mt5.TIMEFRAME_M1 if mt5 else 0

        try:
            # Get current time
            utc_to = datetime.now()
            utc_from = utc_to - timedelta(days=7)  # Last 7 days

            # Fetch rates
            rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)

            if rates is None or len(rates) == 0:
                logger.warning(f"No historical data available for {symbol}")
                return []

            # Convert to list of OHLCVData
            ohlcv_data = []
            for rate in rates[-count:]:  # Get last N bars
                ohlcv_data.append(OHLCVData(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(rate['time']),
                    open=float(rate['open']),
                    high=float(rate['high']),
                    low=float(rate['low']),
                    close=float(rate['close']),
                    volume=int(rate['tick_volume'])
                ))

            logger.debug(f"Fetched {len(ohlcv_data)} historical bars for {symbol}")
            return ohlcv_data

        except Exception as e:
            logger.exception(f"Exception fetching historical data for {symbol}: {e}")
            raise DataError(f"Failed to fetch historical data for {symbol}: {e}")

    async def place_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = ""
    ) -> Optional[int]:
        """
        Place an order on MT5.

        Args:
            symbol: Trading symbol.
            order_type: Order type ('buy' or 'sell').
            volume: Order volume (lots).
            price: Order price (None for market orders).
            sl: Stop loss price.
            tp: Take profit price.
            comment: Order comment.

        Returns:
            int: Order ticket number if successful, None otherwise.

        Raises:
            ConnectionError: If MT5 is not connected.
            OrderError: If order placement fails.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot place order - MT5 not connected")

        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                raise OrderError(f"Symbol {symbol} not found")

            # Normalize symbol
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    raise OrderError(f"Failed to select symbol {symbol}")

            # Determine order type constant
            if order_type.lower() == 'buy':
                mt5_order_type = mt5.ORDER_TYPE_BUY if mt5 else 0
                trade_action = mt5.TRADE_ACTION_DEAL if mt5 else 0
            elif order_type.lower() == 'sell':
                mt5_order_type = mt5.ORDER_TYPE_SELL if mt5 else 1
                trade_action = mt5.TRADE_ACTION_DEAL if mt5 else 0
            else:
                raise OrderError(f"Invalid order type: {order_type}")

            # Get current price for market orders
            if price is None:
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    raise OrderError(f"Failed to get tick data for {symbol}")
                price = tick.ask if order_type.lower() == 'buy' else tick.bid

            # Fill in request structure
            request = {
                "action": trade_action,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC if mt5 else 0,
                "type_filling": mt5.ORDER_FILLING_IOC if mt5 else 0,
            }

            # Send order
            logger.info(f"Placing {order_type} order for {symbol}: volume={volume}, price={price}")
            result = mt5.order_send(request)

            if result is None:
                error = mt5.last_error()
                raise OrderError(f"Order send failed: {error}")

            # Check if order was successful
            # TRADE_RETCODE_DONE is typically 1000 in MT5
            # Use 1000 as default if we're in a test/mock environment
            trade_retcode_done = 1000
            if hasattr(mt5, 'TRADE_RETCODE_DONE') and isinstance(mt5.TRADE_RETCODE_DONE, int):
                trade_retcode_done = mt5.TRADE_RETCODE_DONE

            if result.retcode != trade_retcode_done:
                raise OrderError(
                    f"Order rejected: {result.retcode} - {result.comment}"
                )

            logger.success(f"Order placed successfully: ticket={result.order}")
            return result.order

        except OrderError:
            raise
        except Exception as e:
            logger.exception(f"Exception placing order: {e}")
            raise OrderError(f"Failed to place order: {e}")

    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get open positions.

        Args:
            symbol: Optional symbol filter. If None, returns all positions.

        Returns:
            List[Position]: List of open positions.

        Raises:
            ConnectionError: If MT5 is not connected.
            DataError: If data retrieval fails.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot fetch positions - MT5 not connected")

        try:
            positions = mt5.positions_get(symbol=symbol if symbol else "")

            if positions is None or len(positions) == 0:
                logger.debug(f"No open positions found for {symbol if symbol else 'all symbols'}")
                return []

            # Convert to list of Position objects
            position_list = []
            for pos in positions:
                position_list.append(Position(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    type='buy' if pos.type == 0 else 'sell',
                    volume=pos.volume,
                    price_open=pos.price_open,
                    price_current=pos.price_current,
                    sl=pos.sl,
                    tp=pos.tp,
                    profit=pos.profit,
                    comment=pos.comment,
                    time=datetime.fromtimestamp(pos.time)
                ))

            logger.debug(f"Fetched {len(position_list)} open positions")
            return position_list

        except Exception as e:
            logger.exception(f"Exception fetching positions: {e}")
            raise DataError(f"Failed to fetch positions: {e}")

    async def get_account_info(self) -> AccountInfo:
        """
        Get account information.

        Returns:
            AccountInfo: Account information.

        Raises:
            ConnectionError: If MT5 is not connected.
            DataError: If data retrieval fails.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot fetch account info - MT5 not connected")

        try:
            account = mt5.account_info()
            if not account:
                raise DataError("Failed to get account info")

            terminal_info = mt5.terminal_info()
            company = terminal_info.company if terminal_info else "Unknown"
            server = terminal_info.trade_server if terminal_info else "Unknown"

            account_info = AccountInfo(
                balance=account.balance,
                equity=account.equity,
                margin=account.margin,
                free_margin=account.margin_free,
                margin_level=account.margin_level if account.margin > 0 else 0,
                profit=account.profit,
                currency=account.currency,
                company=company,
                server=server
            )

            logger.debug(
                f"Account info: balance={account_info.balance:.2f}, "
                f"equity={account_info.equity:.2f}, profit={account_info.profit:.2f}"
            )
            return account_info

        except Exception as e:
            logger.exception(f"Exception fetching account info: {e}")
            raise DataError(f"Failed to fetch account info: {e}")

    async def close_position(self, ticket: int) -> bool:
        """
        Close a position by ticket number.

        Args:
            ticket: Position ticket number.

        Returns:
            bool: True if successful, False otherwise.

        Raises:
            ConnectionError: If MT5 is not connected.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot close position - MT5 not connected")

        try:
            # Get position
            position = mt5.positions_get(ticket=ticket)
            if not position or len(position) == 0:
                logger.error(f"Position {ticket} not found")
                return False

            pos = position[0]

            # Determine close order type
            close_type = mt5.ORDER_TYPE_SELL if mt5 else 1 if pos.type == 0 else mt5.ORDER_TYPE_BUY if mt5 else 0

            # Get current price
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                logger.error(f"Failed to get tick data for {pos.symbol}")
                return False

            close_price = tick.bid if pos.type == 0 else tick.ask

            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL if mt5 else 0,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC if mt5 else 0,
                "type_filling": mt5.ORDER_FILLING_IOC if mt5 else 0,
            }

            # Send close order
            result = mt5.order_send(request)

            # Check if close order was successful
            # TRADE_RETCODE_DONE is typically 1000 in MT5
            trade_retcode_done = 1000
            if hasattr(mt5, 'TRADE_RETCODE_DONE') and isinstance(mt5.TRADE_RETCODE_DONE, int):
                trade_retcode_done = mt5.TRADE_RETCODE_DONE

            if result is None or result.retcode != trade_retcode_done:
                error = mt5.last_error()
                logger.error(f"Failed to close position {ticket}: {error}")
                return False

            logger.success(f"Position {ticket} closed successfully")
            return True

        except Exception as e:
            logger.exception(f"Exception closing position {ticket}: {e}")
            return False

    def _shutdown(self) -> None:
        """Shutdown MT5 connection."""
        try:
            if mt5:
                mt5.shutdown()
                logger.debug("MT5 connection shutdown")
        except Exception as e:
            logger.warning(f"Exception during MT5 shutdown: {e}")

    async def shutdown(self) -> None:
        """Cleanup and shutdown MT5 service."""
        logger.info("Shutting down MT5 service")
        self._status = ConnectionStatus.DISCONNECTED
        self._shutdown()


# Global MT5 service instance
_mt5_service: Optional[MT5Service] = None


def get_mt5_service() -> MT5Service:
    """
    Get global MT5 service instance.

    Returns:
        MT5Service: Global MT5 service instance.
    """
    global _mt5_service
    if _mt5_service is None:
        _mt5_service = MT5Service()
    return _mt5_service
