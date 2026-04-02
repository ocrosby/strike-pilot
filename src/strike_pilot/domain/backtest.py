"""Domain models and pure functions for backtesting.

Backtesting simulates running the recommendation engine over a historical
date range and measuring trade outcomes against actual closing prices.
All P&L calculations are pure functions with no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from strike_pilot.domain.models import RiskParameters, SpreadRecommendation, SpreadType


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a single backtest run."""

    symbol: str
    start_date: str  # ISO date YYYY-MM-DD
    end_date: str  # ISO date YYYY-MM-DD
    risk_params: RiskParameters
    strategy: str = "delta"
    spread_width: float = 10.0
    target_short_delta: float = 0.20


@dataclass(frozen=True)
class TradeRecord:
    """A single trade entered during a backtest, including its resolved outcome."""

    entry_date: str  # ISO date of signal / entry
    expiry_date: str  # ISO date of options expiry
    spread_type: str
    short_strike: float
    long_strike: float
    net_credit: float
    max_loss: float
    expiry_close: float | None  # None when expiry data was unavailable
    pnl: float | None  # None when expiry_close is unavailable ("open" trade)


@dataclass
class BacktestResult:
    """Aggregated results from a completed backtest run."""

    config: BacktestConfig
    trades: list[TradeRecord] = field(default_factory=list)

    @property
    def total_trades(self) -> int:
        """Total number of recommended trades entered."""
        return len(self.trades)

    @property
    def _completed(self) -> list[TradeRecord]:
        return [t for t in self.trades if t.pnl is not None]

    @property
    def winning_trades(self) -> int:
        """Trades that closed with a positive P&L."""
        return sum(1 for t in self._completed if t.pnl is not None and t.pnl > 0)

    @property
    def losing_trades(self) -> int:
        """Trades that closed with a negative P&L."""
        return sum(1 for t in self._completed if t.pnl is not None and t.pnl < 0)

    @property
    def win_rate(self) -> float:
        """Fraction of completed trades that were profitable (0.0-1.0)."""
        completed = self._completed
        if not completed:
            return 0.0
        return self.winning_trades / len(completed)

    @property
    def total_pnl(self) -> float:
        """Sum of P&L across all completed trades."""
        return sum(t.pnl for t in self._completed if t.pnl is not None)

    @property
    def average_credit(self) -> float:
        """Mean net credit collected across all entered trades."""
        if not self.trades:
            return 0.0
        return sum(t.net_credit for t in self.trades) / len(self.trades)

    @property
    def average_pnl(self) -> float:
        """Mean P&L across completed trades."""
        completed = self._completed
        if not completed:
            return 0.0
        return self.total_pnl / len(completed)

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough decline in cumulative P&L.

        Computed by walking the P&L series in entry order, tracking the
        running peak and measuring each dip from that peak. Returns 0.0
        when there are no completed trades or no losing streak.
        """
        pnls = [t.pnl for t in self._completed if t.pnl is not None]
        if not pnls:
            return 0.0
        peak = 0.0
        current = 0.0
        max_dd = 0.0
        for pnl in pnls:
            current += pnl
            peak = max(peak, current)
            max_dd = max(max_dd, peak - current)
        return max_dd


def simulate_pnl(recommendation: SpreadRecommendation, expiry_close: float) -> float:
    """Compute realized P&L for a credit spread given the underlying price at expiry.

    For a bull put spread:
        P&L = net_credit - max(0, short_strike - S)*100 + max(0, long_strike - S)*100

    For a bear call spread:
        P&L = net_credit - max(0, S - short_strike)*100 + max(0, S - long_strike)*100

    Args:
        recommendation: The entered credit spread.
        expiry_close: Underlying closing price on the expiry date.

    Returns:
        Realized P&L in dollars (positive = profit, negative = loss).
    """
    if recommendation.spread_type == SpreadType.BULL_PUT:
        short_value = max(0.0, recommendation.short_leg.strike - expiry_close) * 100
        long_value = max(0.0, recommendation.long_leg.strike - expiry_close) * 100
    else:  # BEAR_CALL
        short_value = max(0.0, expiry_close - recommendation.short_leg.strike) * 100
        long_value = max(0.0, expiry_close - recommendation.long_leg.strike) * 100
    return recommendation.net_credit - short_value + long_value
