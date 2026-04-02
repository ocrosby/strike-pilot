"""Unit tests for adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from strike_pilot.adapters.clock import FixedClock, SystemClock
from strike_pilot.adapters.market_data import StaticMarketDataAdapter
from strike_pilot.adapters.options_chain import StaticOptionsChainAdapter
from strike_pilot.adapters.presenters import ConsolePresenter, JsonPresenter
from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    NoTradeSignal,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)
from strike_pilot.ports.interfaces import Clock, MarketDataProvider, OptionsChainProvider


class TestSystemClock:
    def test_returns_datetime(self) -> None:
        clock = SystemClock()
        now = clock.now()
        assert isinstance(now, datetime)

    def test_implements_clock_protocol(self) -> None:
        clock = SystemClock()
        assert isinstance(clock, Clock)


class TestFixedClock:
    def test_returns_fixed_time(self) -> None:
        fixed = datetime(2024, 1, 19, 10, 30, 0, tzinfo=UTC)
        clock = FixedClock(fixed)
        assert clock.now() == fixed

    def test_implements_clock_protocol(self) -> None:
        clock = FixedClock(datetime.now(tz=UTC))
        assert isinstance(clock, Clock)


class TestStaticMarketDataAdapter:
    def test_returns_spx_snapshot(self) -> None:
        adapter = StaticMarketDataAdapter()
        snapshot = adapter.get_snapshot("SPX")
        assert snapshot.symbol == "SPX"
        assert snapshot.price > 0

    def test_unknown_symbol_returns_default(self) -> None:
        adapter = StaticMarketDataAdapter()
        snapshot = adapter.get_snapshot("UNKNOWN")
        assert snapshot.symbol == "UNKNOWN"
        assert snapshot.price > 0

    def test_implements_market_data_provider(self) -> None:
        adapter = StaticMarketDataAdapter()
        assert isinstance(adapter, MarketDataProvider)


class TestStaticOptionsChainAdapter:
    def test_returns_chain_with_strikes(self) -> None:
        adapter = StaticOptionsChainAdapter()
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert len(chain.strikes) > 0
        assert chain.symbol == "SPX"
        assert chain.expiry == "2024-01-19"

    def test_has_premiums(self) -> None:
        adapter = StaticOptionsChainAdapter()
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert len(chain.call_premiums) > 0
        assert len(chain.put_premiums) > 0

    def test_has_deltas(self) -> None:
        adapter = StaticOptionsChainAdapter()
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert len(chain.call_deltas) > 0
        assert len(chain.put_deltas) > 0

    def test_implements_options_chain_provider(self) -> None:
        adapter = StaticOptionsChainAdapter()
        assert isinstance(adapter, OptionsChainProvider)


class TestConsolePresenter:
    def test_present_bias(self, capsys: pytest.CaptureFixture) -> None:
        presenter = ConsolePresenter()
        bias = MarketBias(
            direction=BiasDirection.BULLISH,
            confidence=ConfidenceScore(0.8),
            rationale="Test rationale",
        )
        presenter.present_bias(bias)
        captured = capsys.readouterr()
        assert "BULLISH" in captured.out
        assert "80.0%" in captured.out

    def test_present_no_trade(self, capsys: pytest.CaptureFixture) -> None:
        presenter = ConsolePresenter()
        signal = NoTradeSignal(reason="Low confidence")
        presenter.present_recommendation(signal)
        captured = capsys.readouterr()
        assert "NO TRADE" in captured.out
        assert "Low confidence" in captured.out

    def test_present_spread_recommendation(self, capsys: pytest.CaptureFixture) -> None:
        presenter = ConsolePresenter()
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        short_leg = SpreadLeg(
            strike=5200.0, expiry="2024-01-19", option_type="put", action="sell", premium=3.0
        )
        long_leg = SpreadLeg(
            strike=5195.0, expiry="2024-01-19", option_type="put", action="buy", premium=1.5
        )
        rec = SpreadRecommendation(
            spread_type=SpreadType.BULL_PUT,
            short_leg=short_leg,
            long_leg=long_leg,
            net_credit=150.0,
            max_loss=350.0,
            bias=bias,
        )
        presenter.present_recommendation(rec)
        captured = capsys.readouterr()
        assert "SPREAD TRADE" in captured.out
        assert "150.00" in captured.out


class TestJsonPresenter:
    def test_present_bias_json(self, capsys: pytest.CaptureFixture) -> None:
        presenter = JsonPresenter()
        bias = MarketBias(
            direction=BiasDirection.BULLISH,
            confidence=ConfidenceScore(0.8),
            rationale="Strong signal",
        )
        presenter.present_bias(bias)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["bias"]["direction"] == "bullish"
        assert data["bias"]["confidence"] == 0.8

    def test_present_no_trade_json(self, capsys: pytest.CaptureFixture) -> None:
        presenter = JsonPresenter()
        signal = NoTradeSignal(reason="Neutral")
        presenter.present_recommendation(signal)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["recommendation"]["action"] == "no_trade"

    def test_present_recommendation_json(self, capsys: pytest.CaptureFixture) -> None:
        presenter = JsonPresenter()
        bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
        short_leg = SpreadLeg(
            strike=5200.0, expiry="2024-01-19", option_type="put", action="sell", premium=3.0
        )
        long_leg = SpreadLeg(
            strike=5195.0, expiry="2024-01-19", option_type="put", action="buy", premium=1.5
        )
        rec = SpreadRecommendation(
            spread_type=SpreadType.BULL_PUT,
            short_leg=short_leg,
            long_leg=long_leg,
            net_credit=150.0,
            max_loss=350.0,
            bias=bias,
        )
        presenter.present_recommendation(rec)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["recommendation"]["action"] == "trade"
        assert data["recommendation"]["net_credit"] == 150.0
