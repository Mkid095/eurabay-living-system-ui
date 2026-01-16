"""
Position Monitoring Loop for active trade management.

This module implements the continuous monitoring loop that checks all open
positions every 5 seconds and executes all active management checks.
"""

import asyncio
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .trade_state import TradePosition, TradeState
from .active_trade_manager import ActiveTradeManager, MT5Position
from .trailing_stop_manager import TrailingStopManager, TrailingStopConfig
from .breakeven_manager import BreakevenManager, BreakevenConfig
from .partial_profit_manager import PartialProfitManager, PartialProfitConfig
from .holding_time_optimizer import HoldingTimeOptimizer, HoldingTimeConfig, MarketRegime
from .scale_in_manager import ScaleInManager, ScaleInConfig
from .scale_out_manager import ScaleOutManager, ScaleOutConfig


# Configure logging
logger = logging.getLogger(__name__)


class MonitoringAction(Enum):
    """Types of monitoring actions that can be executed."""

    TRAILING_STOP = "trailing_stop"
    BREAKEVEN = "breakeven"
    PARTIAL_PROFIT = "partial_profit"
    HOLDING_TIME = "holding_time"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    SL_HIT = "sl_hit"
    TP_HIT = "tp_hit"


@dataclass
class MonitoringActionRecord:
    """
    Record of a monitoring action executed.

    Attributes:
        ticket: Position ticket number
        action_type: Type of action executed
        description: Description of what was done
        result: Result of the action (success/failure/none)
        timestamp: When the action was executed
    """

    ticket: int
    action_type: MonitoringAction
    description: str
    result: str
    timestamp: datetime


@dataclass
class PositionMonitoringConfig:
    """
    Configuration for position monitoring loop behavior.

    Attributes:
        interval_seconds: Monitoring loop interval in seconds (default: 5.0)
        trailing_stop_config: Trailing stop configuration
        breakeven_config: Breakeven configuration
        partial_profit_config: Partial profit configuration
        holding_time_config: Holding time configuration
        scale_in_config: Scale-in configuration
        scale_out_config: Scale-out configuration
        default_regime: Default market regime for holding time (default: RANGING)
        enable_trailing_stop: Enable trailing stop checks (default: True)
        enable_breakeven: Enable breakeven checks (default: True)
        enable_partial_profit: Enable partial profit checks (default: True)
        enable_holding_time: Enable holding time checks (default: True)
        enable_scale_in: Enable scale-in checks (default: False)
        enable_scale_out: Enable scale-out checks (default: False)
    """

    interval_seconds: float = 5.0
    trailing_stop_config: TrailingStopConfig = None
    breakeven_config: BreakevenConfig = None
    partial_profit_config: PartialProfitConfig = None
    holding_time_config: HoldingTimeConfig = None
    scale_in_config: ScaleInConfig = None
    scale_out_config: ScaleOutConfig = None
    default_regime: MarketRegime = MarketRegime.RANGING
    enable_trailing_stop: bool = True
    enable_breakeven: bool = True
    enable_partial_profit: bool = True
    enable_holding_time: bool = True
    enable_scale_in: bool = False
    enable_scale_out: bool = False

    def __post_init__(self):
        """Initialize default configs if not provided."""
        if self.trailing_stop_config is None:
            self.trailing_stop_config = TrailingStopConfig()
        if self.breakeven_config is None:
            self.breakeven_config = BreakevenConfig()
        if self.partial_profit_config is None:
            self.partial_profit_config = PartialProfitConfig()
        if self.holding_time_config is None:
            self.holding_time_config = HoldingTimeConfig()
        if self.scale_in_config is None:
            self.scale_in_config = ScaleInConfig()
        if self.scale_out_config is None:
            self.scale_out_config = ScaleOutConfig()


@dataclass
class MonitoringLoopStats:
    """
    Statistics for the monitoring loop.

    Attributes:
        iterations: Number of loop iterations completed
        positions_monitored: Total number of positions monitored
        actions_executed: Total number of actions executed
        errors: Number of errors encountered
        start_time: When the monitoring loop started
        last_iteration_time: Time of last iteration
    """

    iterations: int = 0
    positions_monitored: int = 0
    actions_executed: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    last_iteration_time: Optional[datetime] = None


class PositionMonitoringLoop:
    """
    Continuous monitoring loop that checks all open positions every 5 seconds.

    Features:
    - Runs monitoring loop every 5 seconds (configurable)
    - Fetches all open positions from MT5
    - For each position, runs all active management checks:
      * Trailing stop update
      * Breakeven check
      * Partial profit triggers
      * Holding time limits
      * Scale-in/scale-out triggers
      * Stop loss / take profit hits
    - Executes required actions via MT5
    - Logs all monitoring activity
    - Handles MT5 errors gracefully
    - Tracks monitoring statistics

    Usage:
        loop = PositionMonitoringLoop(mt5_connector, active_trade_manager)
        config = PositionMonitoringConfig()

        # Start monitoring
        await loop.start_monitoring(config)

        # Stop monitoring
        await loop.stop_monitoring()
    """

    def __init__(
        self,
        mt5_connector: Optional["MT5Connector"] = None,
        active_trade_manager: Optional[ActiveTradeManager] = None,
    ):
        """
        Initialize the PositionMonitoringLoop.

        Args:
            mt5_connector: MT5 API connector instance (optional, for testing)
            active_trade_manager: ActiveTradeManager instance for position tracking
        """
        self._mt5 = mt5_connector
        self._active_trade_manager = active_trade_manager

        # Initialize managers
        self._trailing_stop_manager = TrailingStopManager(mt5_connector)
        self._breakeven_manager = BreakevenManager(mt5_connector)
        self._partial_profit_manager = PartialProfitManager(mt5_connector)
        self._holding_time_optimizer = HoldingTimeOptimizer(mt5_connector)
        self._scale_in_manager = ScaleInManager(mt5_connector)
        self._scale_out_manager = ScaleOutManager(mt5_connector)

        # Monitoring state
        self._is_monitoring: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._config: PositionMonitoringConfig = PositionMonitoringConfig()

        # Action history
        self._action_history: list[MonitoringActionRecord] = []

        # Statistics
        self._stats = MonitoringLoopStats()

        logger.info("PositionMonitoringLoop initialized")

    def set_action_callback(
        self, callback: Callable[[MonitoringActionRecord], None]
    ) -> None:
        """
        Set callback for monitoring actions.

        Args:
            callback: Function to call when an action is executed
        """
        self._on_action_callback = callback
        logger.debug("Action callback registered")

    async def start_monitoring(self, config: PositionMonitoringConfig) -> None:
        """
        Start the monitoring loop in the background.

        Args:
            config: PositionMonitoringConfig with monitoring parameters
        """
        if self._is_monitoring:
            logger.warning("Monitoring already active, ignoring start request")
            return

        self._config = config
        self._stats.start_time = datetime.utcnow()

        logger.info(
            f"Starting position monitoring loop with {config.interval_seconds}s interval"
        )
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """
        Stop the monitoring loop.

        Signals the monitoring loop to stop and waits for completion.
        """
        if not self._is_monitoring:
            logger.warning("Monitoring not active, ignoring stop request")
            return

        logger.info("Stopping position monitoring loop")
        self._is_monitoring = False

        if self._monitor_task:
            await asyncio.wait_for(self._monitor_task, timeout=30.0)
            self._monitor_task = None

        logger.info("Position monitoring loop stopped")

    async def _monitoring_loop(self) -> None:
        """
        Main monitoring loop that runs continuously.

        This is the core method that:
        1. Fetches all open positions from MT5
        2. For each position, runs all enabled management checks
        3. Executes required actions via MT5
        4. Logs all monitoring activity
        5. Handles errors gracefully

        This runs continuously until stop_monitoring() is called.
        """
        logger.info("Monitoring loop started")

        while self._is_monitoring:
            try:
                iteration_start = datetime.utcnow()

                # Fetch open positions from MT5
                if self._active_trade_manager:
                    mt5_positions = await self._active_trade_manager.fetch_open_positions()
                else:
                    logger.warning("ActiveTradeManager not configured, skipping position fetch")
                    mt5_positions = []

                logger.info(f"Monitoring {len(mt5_positions)} open positions")

                # Process each position
                for mt5_pos in mt5_positions:
                    await self._process_position(mt5_pos)

                # Update statistics
                self._stats.iterations += 1
                self._stats.positions_monitored += len(mt5_positions)
                self._stats.last_iteration_time = datetime.utcnow()

                # Calculate iteration duration
                iteration_duration = (
                    datetime.utcnow() - iteration_start
                ).total_seconds()

                logger.info(
                    f"Iteration {self._stats.iterations} completed in "
                    f"{iteration_duration:.2f}s, "
                    f"{self._stats.actions_executed} actions executed"
                )

                # Wait for next iteration
                await asyncio.sleep(self._config.interval_seconds)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self._stats.errors += 1
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Continue monitoring despite errors
                await asyncio.sleep(self._config.interval_seconds)

        logger.info("Monitoring loop ended")

    async def _process_position(self, mt5_pos: MT5Position) -> None:
        """
        Process a single position through all management checks.

        Args:
            mt5_pos: MT5Position to process
        """
        try:
            # Get or create TradePosition
            if self._active_trade_manager:
                position = self._active_trade_manager.get_position(mt5_pos.ticket)
                if position is None:
                    # Convert MT5 position to TradePosition
                    position = (
                        self._active_trade_manager._convert_mt5_to_trade_position(
                            mt5_pos
                        )
                    )
            else:
                logger.warning(
                    f"ActiveTradeManager not configured, skipping position {mt5_pos.ticket}"
                )
                return

            # Check for SL/TP hits first
            if await self._check_sl_tp_hits(position):
                return  # Position closed, skip further checks

            # Run all enabled management checks
            await self._run_trailing_stop_check(position)
            await self._run_breakeven_check(position)
            await self._run_partial_profit_check(position)
            await self._run_holding_time_check(position)

            # Scale-in and scale-out are optional features
            if self._config.enable_scale_in:
                await self._run_scale_in_check(position)

            if self._config.enable_scale_out:
                await self._run_scale_out_check(position)

        except Exception as e:
            self._stats.errors += 1
            logger.error(
                f"Error processing position {mt5_pos.ticket}: {e}", exc_info=True
            )

    async def _check_sl_tp_hits(self, position: TradePosition) -> bool:
        """
        Check if stop loss or take profit was hit.

        Args:
            position: TradePosition to check

        Returns:
            True if position was closed (SL/TP hit), False otherwise
        """
        # Check if position is still open
        current_profit = position.profit
        is_loss = current_profit < -abs(position.profit) * 0.9  # Large loss
        is_large_profit = current_profit > abs(position.profit) * 5  # Large profit

        if is_loss or is_large_profit:
            # Likely SL or TP hit - position will be closed by MT5
            action = MonitoringActionRecord(
                ticket=position.ticket,
                action_type=MonitoringAction.SL_HIT if is_loss else MonitoringAction.TP_HIT,
                description=f"{'SL' if is_loss else 'TP'} likely hit (PnL: {current_profit:.2f})",
                result="position_closed",
                timestamp=datetime.utcnow(),
            )
            self._record_action(action)
            return True

        return False

    async def _run_trailing_stop_check(self, position: TradePosition) -> None:
        """
        Run trailing stop check for a position.

        Args:
            position: TradePosition to check
        """
        if not self._config.enable_trailing_stop:
            return

        try:
            update = await self._trailing_stop_manager.update_trailing_stop(
                position, self._config.trailing_stop_config
            )

            if update:
                action = MonitoringActionRecord(
                    ticket=position.ticket,
                    action_type=MonitoringAction.TRAILING_STOP,
                    description=f"Trailing stop updated: {update.old_stop_loss:.5f} -> {update.new_stop_loss:.5f}",
                    result="success",
                    timestamp=datetime.utcnow(),
                )
                self._record_action(action)

        except Exception as e:
            logger.error(f"Error in trailing stop check: {e}", exc_info=True)
            self._record_error(position.ticket, MonitoringAction.TRAILING_STOP, str(e))

    async def _run_breakeven_check(self, position: TradePosition) -> None:
        """
        Run breakeven check for a position.

        Args:
            position: TradePosition to check
        """
        if not self._config.enable_breakeven:
            return

        try:
            update = await self._breakeven_manager.check_breakeven_trigger(
                position, self._config.breakeven_config
            )

            if update:
                action = MonitoringActionRecord(
                    ticket=position.ticket,
                    action_type=MonitoringAction.BREAKEVEN,
                    description=f"Breakeven triggered: {update.old_stop_loss:.5f} -> {update.new_stop_loss:.5f}",
                    result="success",
                    timestamp=datetime.utcnow(),
                )
                self._record_action(action)

        except Exception as e:
            logger.error(f"Error in breakeven check: {e}", exc_info=True)
            self._record_error(position.ticket, MonitoringAction.BREAKEVEN, str(e))

    async def _run_partial_profit_check(self, position: TradePosition) -> None:
        """
        Run partial profit check for a position.

        Args:
            position: TradePosition to check
        """
        if not self._config.enable_partial_profit:
            return

        try:
            update = await self._partial_profit_manager.check_partial_close_triggers(
                position, self._config.partial_profit_config
            )

            if update:
                action = MonitoringActionRecord(
                    ticket=position.ticket,
                    action_type=MonitoringAction.PARTIAL_PROFIT,
                    description=f"Partial profit: {update.close_percentage*100:.1f}% ({update.closed_lots:.2f} lots) at {update.profit_r_multiple:.2f}R",
                    result="success",
                    timestamp=datetime.utcnow(),
                )
                self._record_action(action)

        except Exception as e:
            logger.error(f"Error in partial profit check: {e}", exc_info=True)
            self._record_error(position.ticket, MonitoringAction.PARTIAL_PROFIT, str(e))

    async def _run_holding_time_check(self, position: TradePosition) -> None:
        """
        Run holding time check for a position.

        Args:
            position: TradePosition to check
        """
        if not self._config.enable_holding_time:
            return

        try:
            update = await self._holding_time_optimizer.check_holding_time_limit(
                position, self._config.holding_time_config, self._config.default_regime
            )

            if update:
                action = MonitoringActionRecord(
                    ticket=position.ticket,
                    action_type=MonitoringAction.HOLDING_TIME,
                    description=f"Holding time: {update.close_percentage*100:.1f}% closed at {update.trade_age_seconds}s (max: {update.max_allowed_seconds}s)",
                    result="success",
                    timestamp=datetime.utcnow(),
                )
                self._record_action(action)

        except Exception as e:
            logger.error(f"Error in holding time check: {e}", exc_info=True)
            self._record_error(position.ticket, MonitoringAction.HOLDING_TIME, str(e))

    async def _run_scale_in_check(self, position: TradePosition) -> None:
        """
        Run scale-in check for a position.

        Args:
            position: TradePosition to check
        """
        try:
            operation = await self._scale_in_manager.check_scale_in_trigger(
                position, self._config.scale_in_config
            )

            if operation:
                action = MonitoringActionRecord(
                    ticket=position.ticket,
                    action_type=MonitoringAction.SCALE_IN,
                    description=f"Scale-in: +{operation.scale_percent*100:.1f}% ({operation.added_volume:.2f} lots) at {operation.profit_r_multiple:.2f}R",
                    result="success",
                    timestamp=datetime.utcnow(),
                )
                self._record_action(action)

        except Exception as e:
            logger.error(f"Error in scale-in check: {e}", exc_info=True)
            self._record_error(position.ticket, MonitoringAction.SCALE_IN, str(e))

    async def _run_scale_out_check(self, position: TradePosition) -> None:
        """
        Run scale-out check for a position.

        Args:
            position: TradePosition to check
        """
        try:
            update = await self._scale_out_manager.check_scale_out_trigger(
                position, self._config.scale_out_config
            )

            if update:
                action = MonitoringActionRecord(
                    ticket=position.ticket,
                    action_type=MonitoringAction.SCALE_OUT,
                    description=f"Scale-out: {update.close_percentage*100:.1f}% ({update.closed_lots:.2f} lots) at {update.profit_r_multiple:.2f}R",
                    result="success",
                    timestamp=datetime.utcnow(),
                )
                self._record_action(action)

        except Exception as e:
            logger.error(f"Error in scale-out check: {e}", exc_info=True)
            self._record_error(position.ticket, MonitoringAction.SCALE_OUT, str(e))

    def _record_action(self, action: MonitoringActionRecord) -> None:
        """
        Record a monitoring action.

        Args:
            action: MonitoringActionRecord to record
        """
        self._action_history.append(action)
        self._stats.actions_executed += 1

        logger.info(
            f"Action recorded: {action.action_type.value} for position {action.ticket} - {action.description}"
        )

        # Trigger callback if registered
        if hasattr(self, "_on_action_callback") and self._on_action_callback:
            try:
                self._on_action_callback(action)
            except Exception as e:
                logger.error(f"Error in action callback: {e}", exc_info=True)

    def _record_error(self, ticket: int, action_type: MonitoringAction, error: str) -> None:
        """
        Record a monitoring error.

        Args:
            ticket: Position ticket number
            action_type: Type of action that failed
            error: Error message
        """
        action = MonitoringActionRecord(
            ticket=ticket,
            action_type=action_type,
            description=f"Error: {error}",
            result="error",
            timestamp=datetime.utcnow(),
        )
        self._record_action(action)

    def get_action_history(
        self, ticket: Optional[int] = None
    ) -> list[MonitoringActionRecord]:
        """
        Get monitoring action history.

        Args:
            ticket: Optional ticket number to filter by

        Returns:
            List of MonitoringActionRecord
        """
        if ticket is None:
            return self._action_history.copy()
        return [a for a in self._action_history if a.ticket == ticket]

    def clear_action_history(self) -> None:
        """Clear the action history."""
        self._action_history.clear()
        logger.debug("Action history cleared")

    def get_statistics(self) -> MonitoringLoopStats:
        """
        Get monitoring loop statistics.

        Returns:
            MonitoringLoopStats with current statistics
        """
        return self._stats

    def is_monitoring(self) -> bool:
        """
        Check if the monitoring loop is currently running.

        Returns:
            True if monitoring is active, False otherwise
        """
        return self._is_monitoring

    def get_managers(self) -> dict:
        """
        Get all manager instances.

        Returns:
            Dictionary mapping manager names to instances
        """
        return {
            "trailing_stop": self._trailing_stop_manager,
            "breakeven": self._breakeven_manager,
            "partial_profit": self._partial_profit_manager,
            "holding_time": self._holding_time_optimizer,
            "scale_in": self._scale_in_manager,
            "scale_out": self._scale_out_manager,
        }
