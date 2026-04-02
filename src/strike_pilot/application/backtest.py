"""Backtest use case — runs the recommendation engine over historical data.

Orchestrates:
  1. Fetching daily historical snapshots via HistoricalDataProvider
  2. Running bias analysis for each day
  3. Building a synthetic (or real) options chain for that day's expiry
  4. Running strike selection
  5. Simulating P&L using the actual closing price on expiry day

All dependencies are injected, keeping the use case free of infrastructure
concerns and fully testable without network I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from strike_pilot.domain.backtest import BacktestConfig, BacktestResult, TradeRecord, simulate_pnl
from strike_pilot.domain.expiry import weekly_expiry
from strike_pilot.domain.models import MarketSnapshot, SpreadRecommendation
from strike_pilot.domain.services import BiasStrategy, StrikeSelectionStrategy
from strike_pilot.ports.interfaces import HistoricalDataProvider, OptionsChainProvider


class RunBacktestUseCase:
    """Iterates over historical trading days and records spread trade outcomes.

    Each snapshot in the date range is treated as a potential entry day.
    When the strategy recommends a trade, the position is held to expiry
    (next Friday) and the realized P&L is computed from the closing price
    on that expiry date.
    """

    def __init__(
        self,
        historical_data: HistoricalDataProvider,
        bias_strategy: BiasStrategy,
        chain_factory: Callable[[MarketSnapshot], OptionsChainProvider],
        strike_selector: StrikeSelectionStrategy,
    ) -> None:
        self._historical_data = historical_data
        self._bias_strategy = bias_strategy
        self._chain_factory = chain_factory
        self._strike_selector = strike_selector

    def execute(self, config: BacktestConfig) -> BacktestResult:
        """Run the full backtest for the given configuration.

        Args:
            config: Backtest parameters including symbol, date range, and risk constraints.

        Returns:
            BacktestResult containing all entered trades and computed statistics.
        """
        snapshots = self._historical_data.get_snapshots(
            config.symbol, config.start_date, config.end_date
        )

        trades: list[TradeRecord] = []
        for snapshot in snapshots:
            bias = self._bias_strategy.analyze(snapshot)
            ref_dt = datetime.fromisoformat(snapshot.timestamp)
            expiry = weekly_expiry(ref_dt)

            chain_provider = self._chain_factory(snapshot)
            chain = chain_provider.get_chain(snapshot.symbol, expiry)
            result = self._strike_selector.select_strikes(chain, bias, config.risk_params)

            if not isinstance(result, SpreadRecommendation):
                continue

            expiry_close = self._historical_data.get_close_price(config.symbol, expiry)
            pnl = simulate_pnl(result, expiry_close) if expiry_close is not None else None

            trades.append(
                TradeRecord(
                    entry_date=snapshot.timestamp[:10],
                    expiry_date=expiry,
                    spread_type=result.spread_type.value,
                    short_strike=result.short_leg.strike,
                    long_strike=result.long_leg.strike,
                    net_credit=result.net_credit,
                    max_loss=result.max_loss,
                    expiry_close=expiry_close,
                    pnl=pnl,
                )
            )

        return BacktestResult(config=config, trades=trades)
