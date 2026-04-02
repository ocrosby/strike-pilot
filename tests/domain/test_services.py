"""Unit tests for domain services."""

from __future__ import annotations

from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    MarketSnapshot,
    NoTradeSignal,
    OptionsChain,
    RiskParameters,
    SpreadRecommendation,
)
from strike_pilot.domain.services import (
    DeltaBasedStrikeSelector,
    ProbabilityOfProfitStrikeSelector,
    RiskRewardStrikeSelector,
    SimpleMomentumBiasStrategy,
)


def make_snapshot(
    price: float = 5250.0,
    open_price: float = 5220.0,
    rsi_14: float = 58.0,
    vix: float = 16.0,
    sma_20: float = 5200.0,
    iv_rank: float | None = None,
    iv_percentile: float | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="SPX",
        price=price,
        open_price=open_price,
        high_price=price + 15,
        low_price=price - 15,
        vix=vix,
        timestamp="2024-01-19T10:30:00",
        sma_20=sma_20,
        sma_50=5150.0,
        rsi_14=rsi_14,
        iv_rank=iv_rank,
        iv_percentile=iv_percentile,
    )


def make_options_chain(underlying: float = 5250.0) -> OptionsChain:
    """Build a test options chain with a wide range and realistic premiums.

    Uses a linear delta model: delta = 0.5 - dist/200 (clamped 0.05-0.95).
    Premiums are proportional to delta so net credit > 0 for OTM spreads.
    """
    strikes = [float(s) for s in range(5100, 5415, 5)]
    call_premiums: dict[float, float] = {}
    put_premiums: dict[float, float] = {}
    call_deltas: dict[float, float] = {}
    put_deltas: dict[float, float] = {}

    for strike in strikes:
        call_delta = max(0.05, min(0.95, 0.5 - (strike - underlying) / 200))
        put_delta_abs = max(0.05, min(0.95, 0.5 - (underlying - strike) / 200))
        call_premiums[strike] = round(max(0.5, 30.0 * call_delta), 2)
        put_premiums[strike] = round(max(0.5, 30.0 * put_delta_abs), 2)
        call_deltas[strike] = round(call_delta, 4)
        put_deltas[strike] = round(-put_delta_abs, 4)

    return OptionsChain(
        symbol="SPX",
        expiry="2024-01-19",
        underlying_price=underlying,
        strikes=strikes,
        call_premiums=call_premiums,
        put_premiums=put_premiums,
        call_deltas=call_deltas,
        put_deltas=put_deltas,
    )


def make_risk_params() -> RiskParameters:
    return RiskParameters(
        max_loss_dollars=1000.0,
        min_credit_dollars=10.0,
        max_spread_width=50.0,
        min_confidence_threshold=0.1,
    )


class TestSimpleMomentumBiasStrategy:
    def test_bullish_signal(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        snapshot = make_snapshot(price=5270.0, open_price=5200.0, rsi_14=65.0)
        bias = strategy.analyze(snapshot)
        assert bias.direction == BiasDirection.BULLISH

    def test_bearish_signal(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        snapshot = make_snapshot(price=5180.0, open_price=5250.0, rsi_14=38.0)
        bias = strategy.analyze(snapshot)
        assert bias.direction == BiasDirection.BEARISH

    def test_neutral_signal(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        snapshot = make_snapshot(price=5220.0, open_price=5220.0, rsi_14=50.0, sma_20=5220.0)
        bias = strategy.analyze(snapshot)
        assert bias.direction == BiasDirection.NEUTRAL

    def test_returns_market_bias(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        bias = strategy.analyze(make_snapshot())
        assert isinstance(bias, MarketBias)
        assert isinstance(bias.confidence, ConfidenceScore)

    def test_high_vix_suppresses_confidence(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        low_vix_bias = strategy.analyze(make_snapshot(vix=15.0, price=5270.0, open_price=5200.0))
        high_vix_bias = strategy.analyze(make_snapshot(vix=45.0, price=5270.0, open_price=5200.0))
        assert low_vix_bias.confidence.value >= high_vix_bias.confidence.value

    def test_confidence_in_valid_range(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        bias = strategy.analyze(make_snapshot())
        assert 0.0 <= bias.confidence.value <= 1.0

    def test_high_iv_rank_boosts_confidence(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        no_iv = strategy.analyze(make_snapshot(price=5270.0, open_price=5200.0))
        high_iv = strategy.analyze(make_snapshot(price=5270.0, open_price=5200.0, iv_rank=0.85))
        assert high_iv.confidence.value >= no_iv.confidence.value

    def test_low_iv_rank_suppresses_confidence(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        no_iv = strategy.analyze(make_snapshot(price=5270.0, open_price=5200.0))
        low_iv = strategy.analyze(make_snapshot(price=5270.0, open_price=5200.0, iv_rank=0.10))
        assert low_iv.confidence.value <= no_iv.confidence.value

    def test_iv_rank_in_rationale(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        bias = strategy.analyze(make_snapshot(iv_rank=0.62))
        assert "IVR 62%" in bias.rationale

    def test_iv_percentile_in_rationale(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        bias = strategy.analyze(make_snapshot(iv_percentile=0.55))
        assert "IVP 55%" in bias.rationale

    def test_no_iv_data_no_iv_in_rationale(self) -> None:
        strategy = SimpleMomentumBiasStrategy()
        bias = strategy.analyze(make_snapshot())
        assert "IVR" not in bias.rationale
        assert "IVP" not in bias.rationale


class TestDeltaBasedStrikeSelector:
    def test_bull_put_for_bullish_bias(self) -> None:
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.option_type == "put"

    def test_bear_call_for_bearish_bias(self) -> None:
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.option_type == "call"

    def test_no_trade_for_neutral_bias(self) -> None:
        selector = DeltaBasedStrikeSelector()
        bias = MarketBias(direction=BiasDirection.NEUTRAL, confidence=ConfidenceScore(0.5))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, NoTradeSignal)

    def test_no_trade_when_risk_check_fails(self) -> None:
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.3))
        chain = make_options_chain()
        # Very strict confidence threshold
        risk = RiskParameters(
            max_loss_dollars=500.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.9,
        )
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, NoTradeSignal)

    def test_bull_put_no_trade_when_no_put_strike_available(self) -> None:
        """All strikes above 0.98 * underlying so price fallback also returns None."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        # put_deltas empty; all strikes above 0.98 * 5000 = 4900 -> no candidates
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5000.0,
            strikes=[5200.0, 5300.0],
            call_premiums={5200.0: 5.0, 5300.0: 3.0},
            put_premiums={5200.0: 5.0, 5300.0: 3.0},
            call_deltas={5200.0: 0.4, 5300.0: 0.2},
            put_deltas={},
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, NoTradeSignal)

    def test_bull_put_uses_nearest_long_strike_when_exact_missing(self) -> None:
        """long_strike_target (5195) absent from premiums; nearest below (5190) used."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        # short_strike = 5200 (closest to 0.20 delta); long = 5195 (missing); nearest = 5190
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5250.0,
            strikes=[5185.0, 5190.0, 5200.0],
            call_premiums={5185.0: 3.0, 5190.0: 4.0, 5200.0: 5.0},
            put_premiums={5185.0: 2.0, 5190.0: 3.0, 5200.0: 5.0},
            call_deltas={5185.0: 0.22, 5190.0: 0.21, 5200.0: 0.20},
            put_deltas={5185.0: -0.22, 5190.0: -0.21, 5200.0: -0.20},
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, SpreadRecommendation)
        assert result.long_leg.strike == 5190.0

    def test_bull_put_fallback_to_price_when_put_deltas_empty(self) -> None:
        """Empty put_deltas triggers price-based short-strike selection."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=10.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        # 0.98 * 5000 = 4900; short_strike = max candidate <= 4900
        strikes = [4880.0, 4890.0, 4900.0, 4910.0]
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5000.0,
            strikes=strikes,
            call_premiums=dict.fromkeys(strikes, 3.0),
            put_premiums={4880.0: 2.0, 4890.0: 2.5, 4900.0: 3.0, 4910.0: 4.0},
            call_deltas=dict.fromkeys(strikes, 0.2),
            put_deltas={},
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.strike == 4900.0

    def test_bear_call_no_trade_when_no_call_strike_available(self) -> None:
        """All strikes below 1.02 * underlying so price fallback also returns None."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        # call_deltas empty; all strikes below 1.02 * 5000 = 5100 -> no candidates
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5000.0,
            strikes=[4700.0, 4800.0],
            call_premiums={4700.0: 5.0, 4800.0: 3.0},
            put_premiums={4700.0: 5.0, 4800.0: 3.0},
            call_deltas={},
            put_deltas={4700.0: -0.4, 4800.0: -0.3},
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, NoTradeSignal)

    def test_bear_call_uses_nearest_long_strike_when_exact_missing(self) -> None:
        """long_strike_target (5115) absent from premiums; nearest above (5125) used."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        # short_strike = 5110 (closest to 0.20 call delta); long = 5115 (missing); nearest = 5125
        # net_credit = (8-1)*100=700, max_loss=|5125-5110|*100-700=800 < 1000 -> passes risk check
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5000.0,
            strikes=[5100.0, 5110.0, 5125.0],
            call_premiums={5100.0: 9.0, 5110.0: 8.0, 5125.0: 1.0},
            put_premiums={5100.0: 9.0, 5110.0: 8.0, 5125.0: 1.0},
            call_deltas={5100.0: 0.22, 5110.0: 0.20, 5125.0: 0.18},
            put_deltas={5100.0: -0.22, 5110.0: -0.20, 5125.0: -0.18},
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, SpreadRecommendation)
        assert result.long_leg.strike == 5125.0

    def test_bear_call_no_trade_when_no_long_call_strike_available(self) -> None:
        """long_strike_target absent from premiums and no higher strike exists."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        # short_strike=5200 (only entry at 0.20 delta); long=5205 (missing); no strike >= 5205
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5000.0,
            strikes=[5195.0, 5200.0],
            call_premiums={5195.0: 4.0, 5200.0: 5.0},
            put_premiums={5195.0: 4.0, 5200.0: 5.0},
            call_deltas={5195.0: 0.21, 5200.0: 0.20},
            put_deltas={5195.0: -0.21, 5200.0: -0.20},
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, NoTradeSignal)

    def test_bear_call_fallback_to_price_when_call_deltas_empty(self) -> None:
        """Empty call_deltas triggers price-based short-strike selection."""
        selector = DeltaBasedStrikeSelector(target_short_delta=0.20, spread_width=10.0)
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        # 1.02 * 5000 = 5100; short_strike = min candidate >= 5100
        strikes = [5090.0, 5100.0, 5110.0, 5120.0]
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5000.0,
            strikes=strikes,
            call_premiums={5090.0: 5.0, 5100.0: 4.0, 5110.0: 3.0, 5120.0: 2.0},
            put_premiums=dict.fromkeys(strikes, 3.0),
            call_deltas={},
            put_deltas=dict.fromkeys(strikes, -0.2),
        )
        result = selector.select_strikes(chain, bias, make_risk_params())
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.strike == 5100.0


class TestProbabilityOfProfitStrikeSelector:
    def test_bull_put_for_bullish_bias(self) -> None:
        selector = ProbabilityOfProfitStrikeSelector(target_pop=0.80, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.option_type == "put"

    def test_bear_call_for_bearish_bias(self) -> None:
        selector = ProbabilityOfProfitStrikeSelector(target_pop=0.80, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.option_type == "call"

    def test_short_strike_delta_derived_from_pop(self) -> None:
        """Short strike delta should be ≈ 1 - target_pop."""
        target_pop = 0.80
        selector = ProbabilityOfProfitStrikeSelector(target_pop=target_pop, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        short_delta = abs(chain.put_deltas[result.short_leg.strike])
        assert abs(short_delta - (1.0 - target_pop)) <= 0.05

    def test_rationale_includes_estimated_pop(self) -> None:
        selector = ProbabilityOfProfitStrikeSelector(target_pop=0.80, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert "80%" in result.rationale

    def test_no_trade_for_neutral_bias(self) -> None:
        selector = ProbabilityOfProfitStrikeSelector(target_pop=0.80, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.NEUTRAL, confidence=ConfidenceScore(0.5))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, NoTradeSignal)

    def test_no_trade_when_risk_check_fails(self) -> None:
        selector = ProbabilityOfProfitStrikeSelector(target_pop=0.80, spread_width=5.0)
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.3))
        chain = make_options_chain()
        risk = RiskParameters(
            max_loss_dollars=500.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.9,
        )
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, NoTradeSignal)


class TestRiskRewardStrikeSelector:
    def test_bull_put_for_bullish_bias(self) -> None:
        selector = RiskRewardStrikeSelector(
            target_short_delta=0.20,
            target_rr_ratio=5.0,
            min_spread_width=5.0,
            max_spread_width=25.0,
            step=5.0,
        )
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.option_type == "put"

    def test_bear_call_for_bearish_bias(self) -> None:
        selector = RiskRewardStrikeSelector(
            target_short_delta=0.20,
            target_rr_ratio=5.0,
            min_spread_width=5.0,
            max_spread_width=25.0,
            step=5.0,
        )
        bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert result.short_leg.option_type == "call"

    def test_no_trade_for_neutral_bias(self) -> None:
        selector = RiskRewardStrikeSelector(
            target_short_delta=0.20,
            target_rr_ratio=5.0,
            min_spread_width=5.0,
            max_spread_width=25.0,
            step=5.0,
        )
        bias = MarketBias(direction=BiasDirection.NEUTRAL, confidence=ConfidenceScore(0.5))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, NoTradeSignal)

    def test_rationale_mentions_risk_reward(self) -> None:
        selector = RiskRewardStrikeSelector(
            target_short_delta=0.20,
            target_rr_ratio=5.0,
            min_spread_width=5.0,
            max_spread_width=25.0,
            step=5.0,
        )
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        chain = make_options_chain()
        risk = make_risk_params()
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, SpreadRecommendation)
        assert "R/R" in result.rationale

    def test_no_trade_when_all_widths_fail_risk_check(self) -> None:
        selector = RiskRewardStrikeSelector(
            target_short_delta=0.20,
            target_rr_ratio=5.0,
            min_spread_width=5.0,
            max_spread_width=10.0,
            step=5.0,
        )
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.1))
        chain = make_options_chain()
        risk = RiskParameters(
            max_loss_dollars=10.0,
            min_credit_dollars=500.0,
            max_spread_width=10.0,
            min_confidence_threshold=0.9,
        )
        result = selector.select_strikes(chain, bias, risk)
        assert isinstance(result, NoTradeSignal)
