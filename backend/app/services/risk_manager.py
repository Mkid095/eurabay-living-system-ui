"""
Risk Management Service for EURABAY Living System.

Implements comprehensive risk management including:
- Fixed percentage risk per trade (1-2%)
- ATR-based stop loss calculation
- Kelly Criterion position sizing
- Volatility-based position sizing
- Risk-reward ratio validation
- Trailing stop loss
- Time-based exits
- Maximum daily loss limits
- Position correlation checks
- Maximum concurrent positions limits
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import numpy as np
from loguru import logger

from app.core.config import settings


class RiskDecision(Enum):
    """Risk decision for trade validation."""
    APPROVED = "approved"
    REJECTED_RISK_LIMIT = "rejected_risk_limit"
    REJECTED_DAILY_LOSS = "rejected_daily_loss"
    REJECTED_MAX_POSITIONS = "rejected_max_positions"
    REJECTED_CORRELATION = "rejected_correlation"
    REJECTED_RISK_REWARD = "rejected_risk_reward"


@dataclass
class RiskCalculation:
    """Result of a risk calculation."""
    lot_size: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    risk_percentage: float
    reward_amount: float
    risk_reward_ratio: float
    position_value: float
    margin_required: float
    decision: RiskDecision
    reasons: List[str]
    warnings: List[str]


@dataclass
class TradePosition:
    """Represents an open position for risk analysis."""
    symbol: str
    direction: str
    entry_price: float
    lot_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    profit_loss: float
    entry_time: datetime


class RiskManager:
    """
    Comprehensive risk management service for trading operations.

    Implements multiple risk management strategies to protect capital
    and ensure consistent risk-adjusted returns.
    """

    def __init__(
        self,
        max_risk_per_trade: Optional[float] = None,
        max_daily_loss: Optional[float] = None,
        max_concurrent_positions: Optional[int] = None,
        min_risk_reward_ratio: Optional[float] = None,
        account_balance: float = 10000.0,
    ):
        """
        Initialize RiskManager with risk parameters.

        Args:
            max_risk_per_trade: Maximum risk per trade as decimal (e.g., 0.02 for 2%)
            max_daily_loss: Maximum daily loss as decimal (e.g., 0.05 for 5%)
            max_concurrent_positions: Maximum number of concurrent positions
            min_risk_reward_ratio: Minimum risk-reward ratio (e.g., 1.5 for 1.5:1)
            account_balance: Current account balance
        """
        self.max_risk_per_trade = max_risk_per_trade or settings.MAX_RISK_PER_TRADE
        self.max_daily_loss = max_daily_loss or settings.MAX_DAILY_LOSS
        self.max_concurrent_positions = max_concurrent_positions or settings.MAX_CONCURRENT_POSITIONS
        self.min_risk_reward_ratio = min_risk_reward_ratio or settings.MIN_RISK_REWARD_RATIO
        self.account_balance = account_balance
        self.daily_start_balance = account_balance

        # Track daily P&L
        self.daily_pnl: float = 0.0
        self.daily_trades_count: int = 0

        # Track trailing stops for open positions
        self.trailing_stops: Dict[str, float] = {}

        # Track trade durations for time-based exits
        self.trade_entry_times: Dict[int, datetime] = {}

        logger.info(
            f"RiskManager initialized: max_risk={self.max_risk_per_trade:.2%}, "
            f"max_daily_loss={self.max_daily_loss:.2%}, "
            f"max_positions={self.max_concurrent_positions}"
        )

    def calculate_position_size_fixed_risk(
        self,
        entry_price: float,
        stop_loss: float,
        symbol: str = "V10",
    ) -> RiskCalculation:
        """
        Calculate position size using fixed percentage risk per trade.

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            symbol: Trading symbol

        Returns:
            RiskCalculation with position sizing details
        """
        risk_per_share = abs(entry_price - stop_loss)
        risk_amount = self.account_balance * self.max_risk_per_trade

        # Calculate lot size based on risk
        # For volatility indices, 1 lot = 1 unit per point
        lot_size = risk_amount / risk_per_share if risk_per_share > 0 else 0.01

        # Calculate take profit using minimum risk-reward ratio
        take_profit = self._calculate_take_profit(
            entry_price, stop_loss, self.min_risk_reward_ratio
        )

        # Calculate reward amounts
        reward_amount = abs(take_profit - entry_price) * lot_size
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0

        # Calculate position value and margin
        position_value = entry_price * lot_size
        margin_required = position_value * 0.5  # 50% margin for volatility indices

        # Validate risk-reward ratio
        reasons: List[str] = []
        warnings: List[str] = []
        decision = RiskDecision.APPROVED

        if risk_reward_ratio < self.min_risk_reward_ratio:
            decision = RiskDecision.REJECTED_RISK_REWARD
            reasons.append(
                f"Risk-reward ratio {risk_reward_ratio:.2f} below minimum "
                f"{self.min_risk_reward_ratio:.2f}"
            )

        if lot_size <= 0:
            decision = RiskDecision.REJECTED_RISK_LIMIT
            reasons.append("Calculated lot size is zero or negative")

        if lot_size > 100:  # Sanity check for maximum lot size
            warnings.append(f"Large lot size calculated: {lot_size:.2f}")

        return RiskCalculation(
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            risk_percentage=self.max_risk_per_trade,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward_ratio,
            position_value=position_value,
            margin_required=margin_required,
            decision=decision,
            reasons=reasons,
            warnings=warnings,
        )

    def calculate_stop_loss_atr(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        atr_multiplier: float = 1.5,
    ) -> float:
        """
        Calculate stop loss using Average True Range (ATR).

        Args:
            entry_price: Entry price for the trade
            atr: Current ATR value
            direction: Trade direction ("BUY" or "SELL")
            atr_multiplier: ATR multiplier for stop distance (default 1.5)

        Returns:
            Stop loss price
        """
        stop_distance = atr * atr_multiplier

        if direction.upper() == "BUY":
            stop_loss = entry_price - stop_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance

        logger.debug(
            f"ATR-based stop loss: entry={entry_price:.5f}, "
            f"atr={atr:.5f}, multiplier={atr_multiplier}, "
            f"stop_loss={stop_loss:.5f}"
        )

        return stop_loss

    def calculate_position_size_kelly(
        self,
        win_rate: float,
        average_win: float,
        average_loss: float,
        entry_price: float,
        stop_loss: float,
    ) -> RiskCalculation:
        """
        Calculate position size using Kelly Criterion.

        Kelly Formula: f* = (bp - q) / b
        Where:
            b = average_win / average_loss (odds)
            p = win_rate (probability of winning)
            q = 1 - p (probability of losing)

        Args:
            win_rate: Historical win rate (0-1)
            average_win: Average winning trade amount
            average_loss: Average losing trade amount (positive value)
            entry_price: Entry price for the trade
            stop_loss: Stop loss price

        Returns:
            RiskCalculation with Kelly-based position sizing
        """
        # Calculate odds and Kelly percentage
        if average_loss > 0:
            odds = average_win / average_loss
        else:
            odds = 1.0

        if win_rate <= 0 or win_rate >= 1 or odds <= 0:
            # Fall back to fixed risk if invalid inputs
            logger.warning(
                f"Invalid Kelly inputs: win_rate={win_rate}, odds={odds}. "
                "Falling back to fixed risk."
            )
            return self.calculate_position_size_fixed_risk(entry_price, stop_loss)

        kelly_fraction = (odds * win_rate - (1 - win_rate)) / odds

        # Use half-Kelly for safety (more conservative)
        kelly_fraction = max(0, kelly_fraction) * 0.5

        # Cap at max risk per trade
        kelly_fraction = min(kelly_fraction, self.max_risk_per_trade)

        # Calculate position size
        risk_per_share = abs(entry_price - stop_loss)
        risk_amount = self.account_balance * kelly_fraction
        lot_size = risk_amount / risk_per_share if risk_per_share > 0 else 0.01

        # Calculate take profit
        take_profit = self._calculate_take_profit(
            entry_price, stop_loss, self.min_risk_reward_ratio
        )

        # Calculate reward amounts
        reward_amount = abs(take_profit - entry_price) * lot_size
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0

        # Calculate position value and margin
        position_value = entry_price * lot_size
        margin_required = position_value * 0.5

        reasons: List[str] = []
        warnings: List[str] = []

        if kelly_fraction <= 0:
            warnings.append("Negative Kelly expectation - reducing position size")
            lot_size = 0.01  # Minimum position

        return RiskCalculation(
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            risk_percentage=kelly_fraction,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward_ratio,
            position_value=position_value,
            margin_required=margin_required,
            decision=RiskDecision.APPROVED,
            reasons=reasons,
            warnings=warnings,
        )

    def calculate_position_size_volatility(
        self,
        entry_price: float,
        stop_loss: float,
        volatility: float,
        symbol: str = "V10",
    ) -> RiskCalculation:
        """
        Calculate position size based on market volatility.

        Higher volatility = smaller position size to maintain consistent risk.

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            volatility: Current volatility measure (e.g., standard deviation)
            symbol: Trading symbol

        Returns:
            RiskCalculation with volatility-adjusted position sizing
        """
        # Calculate base position size
        base_calc = self.calculate_position_size_fixed_risk(entry_price, stop_loss)

        # Adjust for volatility
        # Normalize volatility: assume 0.001 is "normal" volatility
        normal_volatility = 0.001
        volatility_factor = normal_volatility / max(volatility, 0.0001)

        # Limit factor to reasonable range (0.5 to 2.0)
        volatility_factor = max(0.5, min(2.0, volatility_factor))

        # Adjust lot size
        adjusted_lot_size = base_calc.lot_size * volatility_factor

        # Recalculate values
        risk_amount = self.account_balance * self.max_risk_per_trade
        reward_amount = abs(base_calc.take_profit - entry_price) * adjusted_lot_size
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0

        position_value = entry_price * adjusted_lot_size
        margin_required = position_value * 0.5

        warnings = list(base_calc.warnings)
        if volatility_factor < 0.8:
            warnings.append(f"High volatility detected: {volatility:.6f}. Position size reduced.")
        elif volatility_factor > 1.2:
            warnings.append(f"Low volatility detected: {volatility:.6f}. Position size increased.")

        return RiskCalculation(
            lot_size=adjusted_lot_size,
            stop_loss=base_calc.stop_loss,
            take_profit=base_calc.take_profit,
            risk_amount=risk_amount,
            risk_percentage=base_calc.risk_percentage,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward_ratio,
            position_value=position_value,
            margin_required=margin_required,
            decision=base_calc.decision,
            reasons=base_calc.reasons,
            warnings=warnings,
        )

    def validate_risk_reward_ratio(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> Tuple[bool, float, List[str]]:
        """
        Validate risk-reward ratio meets minimum requirement.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Tuple of (is_valid, ratio, reasons)
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk <= 0:
            return False, 0.0, ["Invalid stop loss: risk is zero or negative"]

        ratio = reward / risk

        reasons: List[str] = []
        if ratio < self.min_risk_reward_ratio:
            reasons.append(
                f"Risk-reward ratio {ratio:.2f} below minimum {self.min_risk_reward_ratio:.2f}"
            )
            return False, ratio, reasons

        reasons.append(f"Risk-reward ratio {ratio:.2f} meets minimum requirement")
        return True, ratio, reasons

    def calculate_trailing_stop(
        self,
        current_price: float,
        direction: str,
        entry_price: float,
        trail_distance: float = 0.0020,
    ) -> Optional[float]:
        """
        Calculate trailing stop loss price.

        Args:
            current_price: Current market price
            direction: Trade direction ("BUY" or "SELL")
            entry_price: Original entry price
            trail_distance: Trail distance as price difference

        Returns:
            New trailing stop price or None
        """
        # Use trade-specific key for trailing stops to avoid conflicts
        stop_key = f"{direction}_{entry_price}"

        if direction.upper() == "BUY":
            # For long positions, trail stop below current price
            new_stop = current_price - trail_distance

            # Initialize or get old stop
            if stop_key not in self.trailing_stops:
                # First call - set initial stop
                initial_stop = entry_price - trail_distance
                self.trailing_stops[stop_key] = initial_stop
                return initial_stop

            old_stop = self.trailing_stops[stop_key]

            # Only move stop up, never down
            if new_stop > old_stop:
                self.trailing_stops[stop_key] = new_stop
                logger.debug(f"Trailing stop updated: {old_stop:.5f} -> {new_stop:.5f}")
                return new_stop

        else:  # SELL
            # For short positions, trail stop above current price
            new_stop = current_price + trail_distance

            # Initialize or get old stop
            if stop_key not in self.trailing_stops:
                # First call - set initial stop
                initial_stop = entry_price + trail_distance
                self.trailing_stops[stop_key] = initial_stop
                return initial_stop

            old_stop = self.trailing_stops[stop_key]

            # Only move stop down, never up
            if new_stop < old_stop:
                self.trailing_stops[stop_key] = new_stop
                logger.debug(f"Trailing stop updated: {old_stop:.5f} -> {new_stop:.5f}")
                return new_stop

        return None

    def check_time_based_exit(
        self,
        trade_id: int,
        entry_time: datetime,
        max_duration_hours: float = 4.0,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if trade should be closed based on maximum duration.

        Args:
            trade_id: Unique trade identifier
            entry_time: Trade entry timestamp
            max_duration_hours: Maximum trade duration in hours

        Returns:
            Tuple of (should_exit, reason)
        """
        current_time = datetime.utcnow()
        elapsed = (current_time - entry_time).total_seconds() / 3600  # Convert to hours

        if elapsed >= max_duration_hours:
            reason = (
                f"Trade {trade_id} exceeded maximum duration: "
                f"{elapsed:.2f}h >= {max_duration_hours}h"
            )
            logger.warning(reason)
            return True, reason

        return False, None

    def check_daily_loss_limit(
        self,
        current_balance: float,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Check if daily loss limit has been reached.

        Args:
            current_balance: Current account balance

        Returns:
            Tuple of (limit_reached, loss_percentage, message)
        """
        daily_pnl = current_balance - self.daily_start_balance
        loss_percentage = daily_pnl / self.daily_start_balance

        if loss_percentage <= -self.max_daily_loss:
            message = (
                f"Daily loss limit reached: {loss_percentage:.2%} <= "
                f"-{self.max_daily_loss:.2%}. Trading halted."
            )
            logger.error(message)
            return True, loss_percentage, message

        return False, loss_percentage, None

    def check_position_correlation(
        self,
        proposed_symbol: str,
        proposed_direction: str,
        open_positions: List[TradePosition],
        max_correlated_positions: int = 2,
    ) -> Tuple[bool, List[str]]:
        """
        Check if new trade would create excessive correlation.

        Args:
            proposed_symbol: Symbol for proposed trade
            proposed_direction: Direction for proposed trade
            open_positions: List of currently open positions
            max_correlated_positions: Maximum allowed correlated positions

        Returns:
            Tuple of (is_valid, reasons)
        """
        reasons: List[str] = []

        # Count positions in same symbol with same direction
        correlated_count = 0
        for pos in open_positions:
            if pos.symbol == proposed_symbol and pos.direction == proposed_direction:
                correlated_count += 1

        if correlated_count >= max_correlated_positions:
            reasons.append(
                f"Already have {correlated_count} positions in {proposed_symbol} "
                f"{proposed_direction}. Maximum allowed: {max_correlated_positions}"
            )
            return False, reasons

        # Check overall exposure to all volatility indices
        if len(open_positions) >= self.max_concurrent_positions:
            reasons.append(
                f"Maximum concurrent positions reached: {len(open_positions)} "
                f"/ {self.max_concurrent_positions}"
            )
            return False, reasons

        reasons.append(f"Position correlation check passed for {proposed_symbol}")
        return True, reasons

    def check_max_concurrent_positions(
        self,
        open_positions: List[TradePosition],
    ) -> Tuple[bool, int, List[str]]:
        """
        Check if maximum concurrent positions limit would be exceeded.

        Args:
            open_positions: List of currently open positions

        Returns:
            Tuple of (can_open, current_count, reasons)
        """
        current_count = len(open_positions)
        reasons: List[str] = []

        if current_count >= self.max_concurrent_positions:
            reasons.append(
                f"Maximum concurrent positions reached: {current_count} / "
                f"{self.max_concurrent_positions}"
            )
            return False, current_count, reasons

        available = self.max_concurrent_positions - current_count
        reasons.append(f"Can open {available} more position(s)")
        return True, current_count, reasons

    def validate_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        lot_size: float,
        open_positions: List[TradePosition],
        current_balance: Optional[float] = None,
    ) -> RiskCalculation:
        """
        Comprehensive trade validation with all risk checks.

        Args:
            symbol: Trading symbol
            direction: Trade direction
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            lot_size: Proposed lot size
            open_positions: List of currently open positions
            current_balance: Current account balance (optional)

        Returns:
            RiskCalculation with validation results
        """
        if current_balance:
            self.account_balance = current_balance

        reasons: List[str] = []
        warnings: List[str] = []

        # Check 1: Daily loss limit
        limit_reached, loss_pct, message = self.check_daily_loss_limit(self.account_balance)
        if limit_reached:
            return RiskCalculation(
                lot_size=0.0,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=0.0,
                risk_percentage=0.0,
                reward_amount=0.0,
                risk_reward_ratio=0.0,
                position_value=0.0,
                margin_required=0.0,
                decision=RiskDecision.REJECTED_DAILY_LOSS,
                reasons=[message] if message else [],
                warnings=warnings,
            )

        # Check 2: Maximum concurrent positions
        can_open, count, pos_reasons = self.check_max_concurrent_positions(open_positions)
        if not can_open:
            return RiskCalculation(
                lot_size=0.0,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=0.0,
                risk_percentage=0.0,
                reward_amount=0.0,
                risk_reward_ratio=0.0,
                position_value=0.0,
                margin_required=0.0,
                decision=RiskDecision.REJECTED_MAX_POSITIONS,
                reasons=pos_reasons,
                warnings=warnings,
            )

        # Check 3: Position correlation
        is_valid, corr_reasons = self.check_position_correlation(
            symbol, direction, open_positions
        )
        if not is_valid:
            return RiskCalculation(
                lot_size=0.0,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=0.0,
                risk_percentage=0.0,
                reward_amount=0.0,
                risk_reward_ratio=0.0,
                position_value=0.0,
                margin_required=0.0,
                decision=RiskDecision.REJECTED_CORRELATION,
                reasons=corr_reasons,
                warnings=warnings,
            )

        # Check 4: Risk-reward ratio
        is_valid, ratio, rr_reasons = self.validate_risk_reward_ratio(
            entry_price, stop_loss, take_profit
        )
        if not is_valid:
            return RiskCalculation(
                lot_size=lot_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=0.0,
                risk_percentage=0.0,
                reward_amount=0.0,
                risk_reward_ratio=ratio,
                position_value=entry_price * lot_size,
                margin_required=entry_price * lot_size * 0.5,
                decision=RiskDecision.REJECTED_RISK_REWARD,
                reasons=rr_reasons,
                warnings=warnings,
            )

        # All checks passed
        reasons.extend(rr_reasons)
        reasons.extend(pos_reasons)
        reasons.extend(corr_reasons)

        # Calculate risk metrics
        risk_per_share = abs(entry_price - stop_loss)
        risk_amount = risk_per_share * lot_size
        risk_percentage = risk_amount / self.account_balance
        reward_amount = abs(take_profit - entry_price) * lot_size
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0

        # Warn if risk exceeds limit
        if risk_percentage > self.max_risk_per_trade:
            warnings.append(
                f"Proposed risk {risk_percentage:.2%} exceeds limit "
                f"{self.max_risk_per_trade:.2%}"
            )

        return RiskCalculation(
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward_ratio,
            position_value=entry_price * lot_size,
            margin_required=entry_price * lot_size * 0.5,
            decision=RiskDecision.APPROVED,
            reasons=reasons,
            warnings=warnings,
        )

    def _calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        min_ratio: float,
    ) -> float:
        """Calculate take profit based on minimum risk-reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = risk * min_ratio

        if entry_price > stop_loss:  # Long position
            return entry_price + reward
        else:  # Short position
            return entry_price - reward

    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L tracking.

        Args:
            pnl: Profit or loss amount to add
        """
        self.daily_pnl += pnl
        self.daily_trades_count += 1

        logger.info(
            f"Daily P&L updated: {pnl:+.2f} | Total: {self.daily_pnl:+.2f} | "
            f"Trades: {self.daily_trades_count}"
        )

    def reset_daily_tracking(self, new_balance: float) -> None:
        """
        Reset daily tracking at start of new trading day.

        Args:
            new_balance: New account balance for the day
        """
        self.daily_start_balance = new_balance
        self.daily_pnl = 0.0
        self.daily_trades_count = 0
        self.trailing_stops.clear()
        self.trade_entry_times.clear()

        logger.info(
            f"Daily risk tracking reset. New start balance: {new_balance:.2f}"
        )

    def get_risk_summary(self) -> Dict:
        """
        Get summary of current risk state.

        Returns:
            Dictionary with risk metrics
        """
        current_balance = self.daily_start_balance + self.daily_pnl
        loss_pct = self.daily_pnl / self.daily_start_balance if self.daily_start_balance > 0 else 0

        return {
            "account_balance": current_balance,
            "daily_start_balance": self.daily_start_balance,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_percentage": loss_pct * 100,
            "daily_trades_count": self.daily_trades_count,
            "max_risk_per_trade": self.max_risk_per_trade,
            "max_daily_loss": self.max_daily_loss,
            "max_concurrent_positions": self.max_concurrent_positions,
            "min_risk_reward_ratio": self.min_risk_reward_ratio,
            "daily_loss_remaining": self.max_daily_loss + loss_pct if loss_pct < 0 else self.max_daily_loss,
        }
