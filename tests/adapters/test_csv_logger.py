"""Unit tests for the CSV recommendation logger adapter."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from strike_pilot.adapters.csv_logger import CsvRecommendationLogger
from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    NoTradeSignal,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)
from strike_pilot.ports.interfaces import RecommendationLogger


def _make_bias() -> MarketBias:
    return MarketBias(
        direction=BiasDirection.BULLISH,
        confidence=ConfidenceScore(0.8),
        rationale="Strong momentum",
    )


def _make_recommendation(bias: MarketBias) -> SpreadRecommendation:
    return SpreadRecommendation(
        spread_type=SpreadType.BULL_PUT,
        short_leg=SpreadLeg(
            strike=5200.0, expiry="2024-01-19", option_type="put", action="sell", premium=3.0
        ),
        long_leg=SpreadLeg(
            strike=5195.0, expiry="2024-01-19", option_type="put", action="buy", premium=1.5
        ),
        net_credit=150.0,
        max_loss=350.0,
        bias=bias,
        rationale="Good setup",
    )


class TestCsvRecommendationLogger:
    def test_implements_recommendation_logger_protocol(self, tmp_path: Path) -> None:
        logger = CsvRecommendationLogger(tmp_path / "log.csv")
        assert isinstance(logger, RecommendationLogger)

    def test_creates_file_with_header_on_first_log(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "log.csv"
        logger = CsvRecommendationLogger(csv_path)
        bias = _make_bias()
        rec = _make_recommendation(bias)

        logger.log(bias, rec)

        with csv_path.open() as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["action"] == "trade"
        assert rows[0]["bias_direction"] == "bullish"
        assert rows[0]["spread_type"] == "bull_put"
        assert rows[0]["short_strike"] == "5200.0"
        assert rows[0]["net_credit"] == "150.0"
        assert rows[0]["rationale"] == "Good setup"

    def test_appends_rows_without_duplicate_headers(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "log.csv"
        logger = CsvRecommendationLogger(csv_path)
        bias = _make_bias()
        rec = _make_recommendation(bias)

        logger.log(bias, rec)
        logger.log(bias, rec)

        with csv_path.open() as fh:
            lines = fh.readlines()

        header_count = sum(1 for line in lines if line.startswith("timestamp,"))
        assert header_count == 1

        with csv_path.open() as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2

    def test_logs_no_trade_signal(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "log.csv"
        logger = CsvRecommendationLogger(csv_path)
        bias = _make_bias()
        signal = NoTradeSignal(reason="Low confidence", bias=bias)

        logger.log(bias, signal)

        with csv_path.open() as fh:
            rows = list(csv.DictReader(fh))

        assert len(rows) == 1
        assert rows[0]["action"] == "no_trade"
        assert rows[0]["rationale"] == "Low confidence"
        assert rows[0]["spread_type"] == ""
        assert rows[0]["short_strike"] == ""

    def test_uses_provided_clock_timestamp(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "log.csv"
        fixed_time = datetime(2024, 6, 15, 10, 30, 0)
        logger = CsvRecommendationLogger(csv_path, clock_now=fixed_time)
        bias = _make_bias()
        rec = _make_recommendation(bias)

        logger.log(bias, rec)

        with csv_path.open() as fh:
            rows = list(csv.DictReader(fh))

        assert rows[0]["timestamp"] == "2024-06-15T10:30:00"
