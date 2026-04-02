"""Unit tests for domain models."""

from __future__ import annotations

import pytest

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


class TestConfidenceScore:
    def test_valid_score(self) -> None:
        score = ConfidenceScore(0.75)
        assert score.value == 0.75

    def test_boundary_zero(self) -> None:
        score = ConfidenceScore(0.0)
        assert score.value == 0.0

    def test_boundary_one(self) -> None:
        score = ConfidenceScore(1.0)
        assert score.value == 1.0

    def test_invalid_negative(self) -> None:
        with pytest.raises(ValueError):
            ConfidenceScore(-0.1)

    def test_invalid_above_one(self) -> None:
        with pytest.raises(ValueError):
            ConfidenceScore(1.1)

    def test_is_high(self) -> None:
        assert ConfidenceScore(0.7).is_high is True
        assert ConfidenceScore(0.69).is_high is False

    def test_is_low(self) -> None:
        assert ConfidenceScore(0.39).is_low is True
        assert ConfidenceScore(0.4).is_low is False

    def test_float_conversion(self) -> None:
        score = ConfidenceScore(0.8)
        assert float(score) == 0.8


class TestMarketBias:
    def test_bullish_bias(self) -> None:
        bias = MarketBias(
            direction=BiasDirection.BULLISH,
            confidence=ConfidenceScore(0.8),
            rationale="Strong uptrend",
        )
        assert bias.direction == BiasDirection.BULLISH
        assert bias.confidence.value == 0.8

    def test_neutral_factory(self) -> None:
        bias = MarketBias.neutral()
        assert bias.direction == BiasDirection.NEUTRAL
        assert bias.confidence.value == 0.5

    def test_neutral_factory_custom_rationale(self) -> None:
        bias = MarketBias.neutral("Custom reason")
        assert bias.rationale == "Custom reason"


class TestRiskParameters:
    def test_valid_params(self) -> None:
        params = RiskParameters(
            max_loss_dollars=500.0,
            min_credit_dollars=50.0,
            max_spread_width=10.0,
        )
        assert params.max_loss_dollars == 500.0

    def test_invalid_max_loss(self) -> None:
        with pytest.raises(ValueError):
            RiskParameters(max_loss_dollars=0.0, min_credit_dollars=50.0, max_spread_width=10.0)

    def test_invalid_min_credit(self) -> None:
        with pytest.raises(ValueError):
            RiskParameters(max_loss_dollars=500.0, min_credit_dollars=0.0, max_spread_width=10.0)

    def test_invalid_spread_width(self) -> None:
        with pytest.raises(ValueError):
            RiskParameters(max_loss_dollars=500.0, min_credit_dollars=50.0, max_spread_width=0.0)

    def test_invalid_confidence_threshold(self) -> None:
        with pytest.raises(ValueError):
            RiskParameters(
                max_loss_dollars=500.0,
                min_credit_dollars=50.0,
                max_spread_width=10.0,
                min_confidence_threshold=1.5,
            )


class TestSpreadRecommendation:
    def _make_recommendation(
        self,
        short_strike: float = 5200.0,
        long_strike: float = 5195.0,
        net_credit: float = 150.0,
        max_loss: float = 350.0,
    ) -> SpreadRecommendation:
        bias = MarketBias(
            direction=BiasDirection.BULLISH,
            confidence=ConfidenceScore(0.8),
        )
        short_leg = SpreadLeg(
            strike=short_strike,
            expiry="2024-01-19",
            option_type="put",
            action="sell",
            premium=3.0,
        )
        long_leg = SpreadLeg(
            strike=long_strike,
            expiry="2024-01-19",
            option_type="put",
            action="buy",
            premium=1.5,
        )
        return SpreadRecommendation(
            spread_type=SpreadType.BULL_PUT,
            short_leg=short_leg,
            long_leg=long_leg,
            net_credit=net_credit,
            max_loss=max_loss,
            bias=bias,
        )

    def test_spread_width(self) -> None:
        rec = self._make_recommendation(short_strike=5200.0, long_strike=5195.0)
        assert rec.spread_width == 5.0

    def test_risk_reward_ratio(self) -> None:
        rec = self._make_recommendation(net_credit=100.0, max_loss=400.0)
        assert rec.risk_reward_ratio == 4.0

    def test_risk_reward_zero_credit(self) -> None:
        rec = self._make_recommendation(net_credit=0.0, max_loss=500.0)
        assert rec.risk_reward_ratio == float("inf")


class TestNoTradeSignal:
    def test_no_trade_signal(self) -> None:
        signal = NoTradeSignal(reason="Neutral bias")
        assert signal.reason == "Neutral bias"
        assert signal.bias is None

    def test_no_trade_signal_with_bias(self) -> None:
        bias = MarketBias.neutral()
        signal = NoTradeSignal(reason="Low confidence", bias=bias)
        assert signal.bias is not None


class TestMarketSnapshot:
    def test_snapshot_creation(self) -> None:
        snap = MarketSnapshot(
            symbol="SPX",
            price=5000.0,
            open_price=4990.0,
            high_price=5010.0,
            low_price=4980.0,
            vix=18.0,
            timestamp="2024-01-19T10:30:00",
        )
        assert snap.symbol == "SPX"
        assert snap.price == 5000.0
        assert snap.additional_signals == {}


class TestOptionsChain:
    def test_options_chain_creation(self) -> None:
        chain = OptionsChain(
            symbol="SPX",
            expiry="2024-01-19",
            underlying_price=5250.0,
        )
        assert chain.symbol == "SPX"
        assert chain.strikes == []
        assert chain.call_premiums == {}
