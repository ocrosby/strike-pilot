"""Unit tests for application use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from strike_pilot.adapters.clock import FixedClock
from strike_pilot.application.use_cases import AnalyzeAndRecommendUseCase
from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    MarketSnapshot,
    NoTradeSignal,
    OptionsChain,
    RiskParameters,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)


def make_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="SPX",
        price=5250.0,
        open_price=5220.0,
        high_price=5265.0,
        low_price=5210.0,
        vix=16.0,
        timestamp="2024-01-19T10:30:00",
        sma_20=5200.0,
        sma_50=5150.0,
        rsi_14=58.0,
    )


def make_chain() -> OptionsChain:
    strikes = [5190.0, 5195.0, 5200.0, 5205.0, 5210.0]
    return OptionsChain(
        symbol="SPX",
        expiry="2024-01-19",
        underlying_price=5250.0,
        strikes=strikes,
        call_premiums=dict.fromkeys(strikes, 5.0),
        put_premiums=dict.fromkeys(strikes, 3.0),
        call_deltas=dict.fromkeys(strikes, 0.2),
        put_deltas=dict.fromkeys(strikes, -0.2),
    )


def make_bullish_bias() -> MarketBias:
    return MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))


def make_recommendation(bias: MarketBias) -> SpreadRecommendation:
    short_leg = SpreadLeg(
        strike=5200.0, expiry="2024-01-19", option_type="put", action="sell", premium=3.0
    )
    long_leg = SpreadLeg(
        strike=5195.0, expiry="2024-01-19", option_type="put", action="buy", premium=1.5
    )
    return SpreadRecommendation(
        spread_type=SpreadType.BULL_PUT,
        short_leg=short_leg,
        long_leg=long_leg,
        net_credit=150.0,
        max_loss=350.0,
        bias=bias,
    )


def make_use_case(
    snapshot: MarketSnapshot | None = None,
    chain: OptionsChain | None = None,
    bias: MarketBias | None = None,
    result: SpreadRecommendation | NoTradeSignal | None = None,
) -> AnalyzeAndRecommendUseCase:
    """Build a use case with all dependencies mocked."""
    snapshot = snapshot or make_snapshot()
    chain = chain or make_chain()
    bias = bias or make_bullish_bias()
    result = result or make_recommendation(bias)

    market_data = MagicMock()
    market_data.get_snapshot.return_value = snapshot

    options_chain = MagicMock()
    options_chain.get_chain.return_value = chain

    bias_strategy = MagicMock()
    bias_strategy.analyze.return_value = bias

    strike_selector = MagicMock()
    strike_selector.select_strikes.return_value = result

    presenter = MagicMock()

    clock = FixedClock(datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC))  # Monday

    return AnalyzeAndRecommendUseCase(
        market_data_provider=market_data,
        options_chain_provider=options_chain,
        bias_strategy=bias_strategy,
        strike_selector=strike_selector,
        presenter=presenter,
        clock=clock,
    )


class TestAnalyzeAndRecommendUseCase:
    def test_execute_returns_bias_and_result(self) -> None:
        use_case = make_use_case()
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        bias, result = use_case.execute(symbol="SPX", risk_params=risk)
        assert isinstance(bias, MarketBias)
        assert isinstance(result, (SpreadRecommendation, NoTradeSignal))

    def test_execute_calls_market_data(self) -> None:
        use_case = make_use_case()
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        use_case.execute(symbol="SPX", risk_params=risk)
        use_case._market_data.get_snapshot.assert_called_once_with("SPX")

    def test_execute_calls_bias_strategy(self) -> None:
        snapshot = make_snapshot()
        use_case = make_use_case(snapshot=snapshot)
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        use_case.execute(symbol="SPX", risk_params=risk)
        use_case._bias_strategy.analyze.assert_called_once_with(snapshot)

    def test_execute_calls_presenter(self) -> None:
        use_case = make_use_case()
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        use_case.execute(symbol="SPX", risk_params=risk)
        use_case._presenter.present_bias.assert_called_once()
        use_case._presenter.present_recommendation.assert_called_once()

    def test_expiry_defaults_to_next_friday(self) -> None:
        use_case = make_use_case()
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        # Clock is fixed to Monday 2024-01-15, next Friday is 2024-01-19
        use_case.execute(symbol="SPX", risk_params=risk, expiry=None)
        use_case._options_chain.get_chain.assert_called_once_with("SPX", "2024-01-19")

    def test_explicit_expiry_is_used(self) -> None:
        use_case = make_use_case()
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        use_case.execute(symbol="SPX", risk_params=risk, expiry="2024-02-16")
        use_case._options_chain.get_chain.assert_called_once_with("SPX", "2024-02-16")

    def test_next_friday_calculation(self) -> None:
        # Monday -> next Friday (4 days away)
        monday = datetime(2024, 1, 15, tzinfo=UTC)
        assert AnalyzeAndRecommendUseCase._next_friday(monday) == "2024-01-19"

    def test_next_friday_from_friday(self) -> None:
        # Friday -> NEXT Friday (7 days away)
        friday = datetime(2024, 1, 19, tzinfo=UTC)
        assert AnalyzeAndRecommendUseCase._next_friday(friday) == "2024-01-26"

    def test_no_trade_result_is_returned(self) -> None:
        no_trade = NoTradeSignal(reason="Neutral bias")
        use_case = make_use_case(result=no_trade)
        risk = RiskParameters(
            max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=10.0
        )
        _, result = use_case.execute(symbol="SPX", risk_params=risk)
        assert isinstance(result, NoTradeSignal)
