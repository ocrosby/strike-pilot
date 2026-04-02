"""End-to-end smoke tests using real static adapters (no mocks).

These tests verify the full wiring from use case through adapters,
catching integration issues that unit tests with mocked dependencies miss.
"""

from __future__ import annotations

from datetime import UTC, datetime

from strike_pilot.adapters.clock import FixedClock
from strike_pilot.adapters.market_data import StaticMarketDataAdapter
from strike_pilot.adapters.options_chain import StaticOptionsChainAdapter
from strike_pilot.adapters.presenters import ConsolePresenter, JsonPresenter
from strike_pilot.application.use_cases import AnalyzeAndRecommendUseCase
from strike_pilot.domain.models import (
    ExpiryCategory,
    ExpiryRecommendation,
    MarketBias,
    NoTradeSignal,
    RiskParameters,
    SpreadRecommendation,
)
from strike_pilot.domain.services import DeltaBasedStrikeSelector, SimpleMomentumBiasStrategy


def _build_use_case(presenter: ConsolePresenter | JsonPresenter) -> AnalyzeAndRecommendUseCase:
    return AnalyzeAndRecommendUseCase(
        market_data_provider=StaticMarketDataAdapter(),
        options_chain_provider=StaticOptionsChainAdapter(),
        bias_strategy=SimpleMomentumBiasStrategy(),
        strike_selector=DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=10.0),
        presenter=presenter,
        clock=FixedClock(datetime(2024, 1, 15, 14, 0, tzinfo=UTC)),
    )


class TestEndToEndSmoke:
    def test_full_pipeline_with_console_presenter(self) -> None:
        use_case = _build_use_case(ConsolePresenter())
        risk_params = RiskParameters(
            max_loss_dollars=1000.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.6,
        )

        bias, result = use_case.execute(symbol="SPX", risk_params=risk_params)

        assert isinstance(bias, MarketBias)
        assert isinstance(result, (SpreadRecommendation, NoTradeSignal))

    def test_full_pipeline_with_json_presenter(self) -> None:
        use_case = _build_use_case(JsonPresenter())
        risk_params = RiskParameters(
            max_loss_dollars=1000.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.6,
        )

        bias, result = use_case.execute(symbol="SPX", risk_params=risk_params)

        assert isinstance(bias, MarketBias)
        assert isinstance(result, (SpreadRecommendation, NoTradeSignal))

    def test_full_pipeline_with_explicit_expiry(self) -> None:
        use_case = _build_use_case(ConsolePresenter())
        risk_params = RiskParameters(
            max_loss_dollars=1000.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.6,
        )

        bias, result = use_case.execute(symbol="SPX", risk_params=risk_params, expiry="2024-02-16")

        assert isinstance(bias, MarketBias)
        assert isinstance(result, (SpreadRecommendation, NoTradeSignal))

    def test_full_pipeline_tight_risk_params_produces_no_trade(self) -> None:
        use_case = _build_use_case(ConsolePresenter())
        risk_params = RiskParameters(
            max_loss_dollars=1.0,
            min_credit_dollars=999.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.99,
        )

        bias, result = use_case.execute(symbol="SPX", risk_params=risk_params)

        assert isinstance(bias, MarketBias)
        assert isinstance(result, NoTradeSignal)

    def test_multi_expiry_all_categories(self) -> None:
        use_case = _build_use_case(ConsolePresenter())
        risk_params = RiskParameters(
            max_loss_dollars=1000.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.6,
        )
        cats = [ExpiryCategory.ZERO_DTE, ExpiryCategory.WEEKLY, ExpiryCategory.MONTHLY]
        bias, recs = use_case.execute_multi(symbol="SPX", risk_params=risk_params, categories=cats)

        assert isinstance(bias, MarketBias)
        assert len(recs) == 3
        for rec in recs:
            assert isinstance(rec, ExpiryRecommendation)
