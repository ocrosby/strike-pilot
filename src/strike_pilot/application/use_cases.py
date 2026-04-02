"""Application use cases for Strike Pilot.

Orchestrates workflows by composing domain services with port adapters.
Use cases depend on port interfaces, not concrete adapters.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from strike_pilot.domain.models import (
    MarketBias,
    NoTradeSignal,
    RiskParameters,
    SpreadRecommendation,
)
from strike_pilot.domain.services import BiasStrategy, StrikeSelectionStrategy
from strike_pilot.ports.interfaces import (
    Clock,
    MarketDataProvider,
    OptionsChainProvider,
    OutputPresenter,
)


class AnalyzeAndRecommendUseCase:
    """Orchestrates the full analyze -> score -> recommend workflow.

    This use case:
    1. Fetches market data via the market data port
    2. Determines bias via the bias strategy
    3. Fetches options chain via the options chain port
    4. Selects strikes via the strike selection strategy
    5. Presents results via the output presenter port

    All dependencies are injected, enabling easy testing and swapping.
    """

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        options_chain_provider: OptionsChainProvider,
        bias_strategy: BiasStrategy,
        strike_selector: StrikeSelectionStrategy,
        presenter: OutputPresenter,
        clock: Clock,
    ) -> None:
        self._market_data = market_data_provider
        self._options_chain = options_chain_provider
        self._bias_strategy = bias_strategy
        self._strike_selector = strike_selector
        self._presenter = presenter
        self._clock = clock

    def execute(
        self,
        symbol: str,
        risk_params: RiskParameters,
        expiry: str | None = None,
    ) -> tuple[MarketBias, SpreadRecommendation | NoTradeSignal]:
        """Run the full analysis and recommendation workflow.

        Args:
            symbol: Market symbol to analyze (e.g., "SPX").
            risk_params: Risk constraints for the trade recommendation.
            expiry: Options expiry date (ISO format). Defaults to next Friday.

        Returns:
            Tuple of (MarketBias, SpreadRecommendation | NoTradeSignal).
        """
        resolved_expiry = expiry or self._next_friday(self._clock.now())

        snapshot = self._market_data.get_snapshot(symbol)
        bias = self._bias_strategy.analyze(snapshot)

        chain = self._options_chain.get_chain(symbol, resolved_expiry)
        result = self._strike_selector.select_strikes(chain, bias, risk_params)

        self._presenter.present_bias(bias)
        self._presenter.present_recommendation(result)

        return bias, result

    @staticmethod
    def _next_friday(from_date: datetime) -> str:
        """Calculate the next Friday from the given date (ISO format)."""
        days_until_friday = (4 - from_date.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        next_friday = from_date + timedelta(days=days_until_friday)
        return next_friday.strftime("%Y-%m-%d")
