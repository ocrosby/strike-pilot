"""Unit tests for alert service adapters."""

from __future__ import annotations

import logging

import pytest

from strike_pilot.adapters.alert import ConsoleAlertService, LoggingAlertService
from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)


def make_bias() -> MarketBias:
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
        rationale="Bull put spread: sell 5200P / buy 5195P",
    )


class TestLoggingAlertService:
    def test_logs_at_info_level(self, caplog: pytest.LogCaptureFixture) -> None:
        service = LoggingAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        with caplog.at_level(logging.INFO):
            service.alert(bias, rec)
        assert len(caplog.records) >= 1
        assert caplog.records[0].levelno == logging.INFO

    def test_log_message_includes_spread_type(self, caplog: pytest.LogCaptureFixture) -> None:
        service = LoggingAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        with caplog.at_level(logging.INFO):
            service.alert(bias, rec)
        assert "bull_put" in caplog.text.lower()

    def test_log_message_includes_net_credit(self, caplog: pytest.LogCaptureFixture) -> None:
        service = LoggingAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        with caplog.at_level(logging.INFO):
            service.alert(bias, rec)
        assert "150" in caplog.text

    def test_custom_logger_name(self, caplog: pytest.LogCaptureFixture) -> None:
        service = LoggingAlertService(logger_name="my.alerts")
        bias = make_bias()
        rec = make_recommendation(bias)
        with caplog.at_level(logging.INFO, logger="my.alerts"):
            service.alert(bias, rec)
        assert any(r.name == "my.alerts" for r in caplog.records)


class TestConsoleAlertService:
    def test_prints_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        service = ConsoleAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        service.alert(bias, rec)
        captured = capsys.readouterr()
        assert captured.out != ""

    def test_output_includes_spread_type(self, capsys: pytest.CaptureFixture[str]) -> None:
        service = ConsoleAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        service.alert(bias, rec)
        captured = capsys.readouterr()
        assert "bull_put" in captured.out.lower()

    def test_output_includes_net_credit(self, capsys: pytest.CaptureFixture[str]) -> None:
        service = ConsoleAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        service.alert(bias, rec)
        captured = capsys.readouterr()
        assert "150" in captured.out

    def test_output_includes_bias_direction(self, capsys: pytest.CaptureFixture[str]) -> None:
        service = ConsoleAlertService()
        bias = make_bias()
        rec = make_recommendation(bias)
        service.alert(bias, rec)
        captured = capsys.readouterr()
        assert "bullish" in captured.out.lower()
