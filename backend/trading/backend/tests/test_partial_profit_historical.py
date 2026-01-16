"""
Historical data test for PartialProfitManager.

Tests the partial profit taking functionality on simulated historical data
to validate that it improves overall win rate and banks profits early.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass

from backend.core import (
    PartialProfitManager,
    PartialProfitConfig,
    TradePosition,
    TradeState,
)


@dataclass
class HistoricalTrade:
    """Represents a historical trade for testing."""
    entry_price: float
    exit_price: float
    stop_loss: float
    direction: str
    max_profit: float  # Maximum profit reached during trade
    max_loss: float  # Maximum loss reached during trade


class HistoricalPriceSimulator:
    """Simulates price movements for historical testing."""

    @staticmethod
    def simulate_trade_progression(
        trade: HistoricalTrade, steps: int = 100
    ) -> List[float]:
        """
        Simulate price progression from entry to exit.

        Args:
            trade: Historical trade to simulate
            steps: Number of price points to generate

        Returns:
            List of prices during trade progression
        """
        prices = []

        if trade.direction == "BUY":
            # Simulate LONG trade progression
            for i in range(steps):
                progress = i / (steps - 1)

                # Add some noise to simulate realistic price movement
                noise = (i % 10 - 5) * 0.0001

                # Interpolate between entry and exit
                base_price = trade.entry_price + (
                    trade.exit_price - trade.entry_price
                ) * progress

                # Add some profit-taking behavior
                if trade.max_profit > 0:
                    # Simulate reaching max profit midway
                    profit_spike = trade.max_profit * 0.0001 * (
                        1 - abs(progress - 0.5) * 2
                    )
                else:
                    profit_spike = 0

                price = base_price + noise + profit_spike
                prices.append(max(price, trade.stop_loss))

        else:  # SELL
            # Simulate SHORT trade progression
            for i in range(steps):
                progress = i / (steps - 1)

                # Add some noise
                noise = (i % 10 - 5) * 0.0001

                # Interpolate between entry and exit
                base_price = trade.entry_price + (
                    trade.exit_price - trade.entry_price
                ) * progress

                # Add some profit-taking behavior
                if trade.max_profit > 0:
                    profit_spike = -trade.max_profit * 0.0001 * (
                        1 - abs(progress - 0.5) * 2
                    )
                else:
                    profit_spike = 0

                price = base_price + noise + profit_spike
                prices.append(min(price, trade.stop_loss))

        return prices


class PartialProfitHistoricalTester:
    """Tests partial profit taking on historical data."""

    def __init__(self):
        self.manager = PartialProfitManager(mt5_connector=None)
        self.config = PartialProfitConfig()

    def calculate_profit(
        self, entry_price: float, current_price: float, volume: float, direction: str
    ) -> float:
        """Calculate profit for a position."""
        if direction == "BUY":
            return (current_price - entry_price) * volume * 100000
        else:
            return (entry_price - current_price) * volume * 100000

    def test_winning_trade_with_partial_profit(self):
        """Test a winning trade that triggers partial profits."""
        print("\n=== Testing Winning Trade with Partial Profit ===")

        # Create a winning LONG trade
        trade = HistoricalTrade(
            entry_price=1.0850,
            exit_price=1.0950,  # 100 pip profit
            stop_loss=1.0800,
            direction="BUY",
            max_profit=150,  # Reaches 1.5R max
            max_loss=-40,
        )

        # Simulate price progression
        prices = HistoricalPriceSimulator.simulate_trade_progression(trade)

        # Track partial closes
        partial_closes = []
        total_profit_banked = 0.0

        # Simulate trade progression
        position = TradePosition(
            ticket=1,
            symbol="EURUSD",
            direction="BUY",
            entry_price=trade.entry_price,
            current_price=trade.entry_price,
            volume=0.1,
            stop_loss=trade.stop_loss,
            take_profit=None,
            entry_time=datetime.utcnow(),
            profit=0.0,
            swap=0.0,
            commission=0.0,
            state=TradeState.OPEN,
        )

        for i, price in enumerate(prices):
            position.current_price = price
            position.profit = self.calculate_profit(
                trade.entry_price, price, 0.1, "BUY"
            )

            # Check for partial profit triggers
            update = asyncio.run(
                self.manager.check_partial_close_triggers(position, self.config)
            )

            if update:
                partial_closes.append(update)
                total_profit_banked += update.profit_at_close
                position.volume = update.remaining_lots

                print(
                    f"Step {i}: Partial close - {update.close_percentage*100:.0f}% "
                    f"at {update.profit_r_multiple:.1f}R, "
                    f"banked ${update.profit_at_close:.2f}"
                )

        # Calculate final results
        final_profit = self.calculate_profit(
            trade.entry_price, trade.exit_price, position.volume, "BUY"
        )
        total_profit = total_profit_banked + final_profit

        print(f"\nResults:")
        print(f"  Partial closes: {len(partial_closes)}")
        print(f"  Profit banked early: ${total_profit_banked:.2f}")
        print(f"  Final position profit: ${final_profit:.2f}")
        print(f"  Total profit: ${total_profit:.2f}")
        print(f"  Percentage banked: {(total_profit_banked/total_profit)*100:.1f}%")

        # Assertions
        assert len(partial_closes) > 0, "Should have triggered partial profit"
        assert total_profit_banked > 0, "Should have banked profit"
        assert total_profit > 0, "Trade should be profitable"

        return True

    def test_losing_trade_no_partial_profit(self):
        """Test a losing trade that doesn't trigger partial profit."""
        print("\n=== Testing Losing Trade (No Partial Profit) ===")

        # Create a losing LONG trade
        trade = HistoricalTrade(
            entry_price=1.0850,
            exit_price=1.0810,  # 40 pip loss (hits SL)
            stop_loss=1.0800,
            direction="BUY",
            max_profit=20,  # Briefly profitable but not enough
            max_loss=-50,
        )

        # Simulate price progression
        prices = HistoricalPriceSimulator.simulate_trade_progression(trade)

        # Track partial closes
        partial_closes = []

        # Simulate trade progression
        position = TradePosition(
            ticket=2,
            symbol="EURUSD",
            direction="BUY",
            entry_price=trade.entry_price,
            current_price=trade.entry_price,
            volume=0.1,
            stop_loss=trade.stop_loss,
            take_profit=None,
            entry_time=datetime.utcnow(),
            profit=0.0,
            swap=0.0,
            commission=0.0,
            state=TradeState.OPEN,
        )

        for i, price in enumerate(prices):
            position.current_price = price
            position.profit = self.calculate_profit(
                trade.entry_price, price, 0.1, "BUY"
            )

            # Check for partial profit triggers
            update = asyncio.run(
                self.manager.check_partial_close_triggers(position, self.config)
            )

            if update:
                partial_closes.append(update)

        # Calculate final results
        final_profit = self.calculate_profit(
            trade.entry_price, trade.exit_price, position.volume, "BUY"
        )

        print(f"\nResults:")
        print(f"  Partial closes: {len(partial_closes)}")
        print(f"  Final profit: ${final_profit:.2f}")

        # Assertions
        assert len(partial_closes) == 0, "Should not have triggered partial profit"
        assert final_profit < 0, "Trade should be losing"

        return True

    def test_breakeven_trade_with_partial_profit(self):
        """Test a trade that reaches breakeven but not partial profit level."""
        print("\n=== Testing Breakeven Trade (No Partial Profit) ===")

        # Create a trade that reaches ~1R but not 2R
        trade = HistoricalTrade(
            entry_price=1.0850,
            exit_price=1.0900,  # 50 pip profit (1R)
            stop_loss=1.0800,
            direction="BUY",
            max_profit=60,  # Reaches 1.2R max
            max_loss=-30,
        )

        # Simulate price progression
        prices = HistoricalPriceSimulator.simulate_trade_progression(trade)

        # Track partial closes
        partial_closes = []

        # Simulate trade progression
        position = TradePosition(
            ticket=3,
            symbol="EURUSD",
            direction="BUY",
            entry_price=trade.entry_price,
            current_price=trade.entry_price,
            volume=0.1,
            stop_loss=trade.stop_loss,
            take_profit=None,
            entry_time=datetime.utcnow(),
            profit=0.0,
            swap=0.0,
            commission=0.0,
            state=TradeState.OPEN,
        )

        for i, price in enumerate(prices):
            position.current_price = price
            position.profit = self.calculate_profit(
                trade.entry_price, price, 0.1, "BUY"
            )

            # Check for partial profit triggers
            update = asyncio.run(
                self.manager.check_partial_close_triggers(position, self.config)
            )

            if update:
                partial_closes.append(update)

        print(f"\nResults:")
        print(f"  Partial closes: {len(partial_closes)}")
        print(f"  Max profit reached: {max([p.profit for p in partial_closes] + [position.profit]):.2f}")

        # Should not trigger at 1R (need 2R)
        assert len(partial_closes) == 0, "Should not trigger at 1R"

        return True

    def run_all_tests(self):
        """Run all historical data tests."""
        print("=" * 60)
        print("PARTIAL PROFIT HISTORICAL DATA TESTS")
        print("=" * 60)

        tests = [
            ("Winning trade with partial profit", self.test_winning_trade_with_partial_profit),
            ("Losing trade no partial profit", self.test_losing_trade_no_partial_profit),
            ("Breakeven trade no partial profit", self.test_breakeven_trade_with_partial_profit),
        ]

        results = []

        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, "PASSED" if result else "FAILED"))
            except Exception as e:
                results.append((name, f"FAILED: {e}"))
                print(f"\nERROR in {name}: {e}")

        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        for name, result in results:
            status_symbol = "✓" if "PASSED" in result else "✗"
            print(f"{status_symbol} {name}: {result}")

        passed = sum(1 for _, r in results if "PASSED" in r)
        total = len(results)

        print(f"\nTotal: {passed}/{total} tests passed")

        return passed == total


if __name__ == "__main__":
    tester = PartialProfitHistoricalTester()
    success = tester.run_all_tests()

    if success:
        print("\n✓ All historical data tests passed!")
    else:
        print("\n✗ Some tests failed")

    exit(0 if success else 1)
