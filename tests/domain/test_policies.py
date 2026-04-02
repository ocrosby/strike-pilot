"""Unit tests for domain policies."""

from __future__ import annotations

from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    RiskParameters,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)
from strike_pilot.domain.policies import (
    is_confidence_sufficient,
    is_credit_adequate,
    is_max_loss_within_limit,
    is_spread_width_valid,
    passes_all_risk_checks,
)


def make_bias(confidence: float, direction: BiasDirection = BiasDirection.BULLISH) -> MarketBias:
    return MarketBias(direction=direction, confidence=ConfidenceScore(confidence))


def make_risk_params(
    max_loss: float = 500.0,
    min_credit: float = 50.0,
    max_width: float = 10.0,
    min_confidence: float = 0.6,
) -> RiskParameters:
    return RiskParameters(
        max_loss_dollars=max_loss,
        min_credit_dollars=min_credit,
        max_spread_width=max_width,
        min_confidence_threshold=min_confidence,
    )


def make_recommendation(
    net_credit: float = 150.0,
    max_loss: float = 350.0,
    short_strike: float = 5200.0,
    long_strike: float = 5195.0,
) -> SpreadRecommendation:
    bias = make_bias(0.8)
    short_leg = SpreadLeg(
        strike=short_strike, expiry="2024-01-19", option_type="put", action="sell", premium=3.0
    )
    long_leg = SpreadLeg(
        strike=long_strike, expiry="2024-01-19", option_type="put", action="buy", premium=1.5
    )
    return SpreadRecommendation(
        spread_type=SpreadType.BULL_PUT,
        short_leg=short_leg,
        long_leg=long_leg,
        net_credit=net_credit,
        max_loss=max_loss,
        bias=bias,
    )


class TestIsConfidenceSufficient:
    def test_sufficient(self) -> None:
        assert is_confidence_sufficient(make_bias(0.7), make_risk_params(min_confidence=0.6))

    def test_exactly_threshold(self) -> None:
        assert is_confidence_sufficient(make_bias(0.6), make_risk_params(min_confidence=0.6))

    def test_insufficient(self) -> None:
        assert not is_confidence_sufficient(make_bias(0.5), make_risk_params(min_confidence=0.6))


class TestIsCreditAdequate:
    def test_adequate(self) -> None:
        rec = make_recommendation(net_credit=100.0)
        assert is_credit_adequate(rec, make_risk_params(min_credit=50.0))

    def test_exactly_minimum(self) -> None:
        rec = make_recommendation(net_credit=50.0)
        assert is_credit_adequate(rec, make_risk_params(min_credit=50.0))

    def test_inadequate(self) -> None:
        rec = make_recommendation(net_credit=30.0)
        assert not is_credit_adequate(rec, make_risk_params(min_credit=50.0))


class TestIsMaxLossWithinLimit:
    def test_within_limit(self) -> None:
        rec = make_recommendation(max_loss=400.0)
        assert is_max_loss_within_limit(rec, make_risk_params(max_loss=500.0))

    def test_at_limit(self) -> None:
        rec = make_recommendation(max_loss=500.0)
        assert is_max_loss_within_limit(rec, make_risk_params(max_loss=500.0))

    def test_exceeds_limit(self) -> None:
        rec = make_recommendation(max_loss=600.0)
        assert not is_max_loss_within_limit(rec, make_risk_params(max_loss=500.0))


class TestIsSpreadWidthValid:
    def test_valid_width(self) -> None:
        rec = make_recommendation(short_strike=5200.0, long_strike=5195.0)
        assert is_spread_width_valid(rec, make_risk_params(max_width=10.0))

    def test_exceeds_width(self) -> None:
        rec = make_recommendation(short_strike=5200.0, long_strike=5185.0)
        assert not is_spread_width_valid(rec, make_risk_params(max_width=10.0))


class TestPassesAllRiskChecks:
    def test_all_pass(self) -> None:
        bias = make_bias(0.8)
        rec = make_recommendation(net_credit=150.0, max_loss=350.0)
        assert passes_all_risk_checks(rec, bias, make_risk_params())

    def test_fails_on_low_confidence(self) -> None:
        bias = make_bias(0.3)
        rec = make_recommendation(net_credit=150.0, max_loss=350.0)
        assert not passes_all_risk_checks(rec, bias, make_risk_params(min_confidence=0.6))

    def test_fails_on_low_credit(self) -> None:
        bias = make_bias(0.8)
        rec = make_recommendation(net_credit=10.0, max_loss=350.0)
        assert not passes_all_risk_checks(rec, bias, make_risk_params(min_credit=50.0))
