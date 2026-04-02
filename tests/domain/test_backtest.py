"""Unit tests for backtest domain models and pure functions."""

from __future__ import annotations

import pytest

from strike_pilot.domain.backtest import BacktestConfig, BacktestResult, TradeRecord, simulate_pnl
from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    RiskParameters,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)


def make_risk_params() -> RiskParameters:
    return RiskParameters(
        max_loss_dollars=1000.0,
        min_credit_dollars=10.0,
        max_spread_width=50.0,
    )


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="SPX",
        start_date="2024-01-15",
        end_date="2024-01-19",
        risk_params=make_risk_params(),
    )


def make_bull_put(
    short: float = 5200.0,
    long: float = 5195.0,
    credit: float = 150.0,
) -> SpreadRecommendation:
    bias = MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))
    max_loss = (short - long) * 100 - credit
    return SpreadRecommendation(
        spread_type=SpreadType.BULL_PUT,
        short_leg=SpreadLeg(
            strike=short, expiry="2024-01-19", option_type="put", action="sell", premium=3.0
        ),
        long_leg=SpreadLeg(
            strike=long, expiry="2024-01-19", option_type="put", action="buy", premium=1.5
        ),
        net_credit=credit,
        max_loss=max_loss,
        bias=bias,
    )


def make_bear_call(
    short: float = 5300.0,
    long: float = 5305.0,
    credit: float = 150.0,
) -> SpreadRecommendation:
    bias = MarketBias(direction=BiasDirection.BEARISH, confidence=ConfidenceScore(0.8))
    max_loss = (long - short) * 100 - credit
    return SpreadRecommendation(
        spread_type=SpreadType.BEAR_CALL,
        short_leg=SpreadLeg(
            strike=short, expiry="2024-01-19", option_type="call", action="sell", premium=3.0
        ),
        long_leg=SpreadLeg(
            strike=long, expiry="2024-01-19", option_type="call", action="buy", premium=1.5
        ),
        net_credit=credit,
        max_loss=max_loss,
        bias=bias,
    )


def make_trade(pnl: float | None, credit: float = 150.0) -> TradeRecord:
    return TradeRecord(
        entry_date="2024-01-15",
        expiry_date="2024-01-19",
        spread_type="bull_put",
        short_strike=5200.0,
        long_strike=5195.0,
        net_credit=credit,
        max_loss=350.0,
        expiry_close=5250.0 if pnl is not None else None,
        pnl=pnl,
    )


# ---------------------------------------------------------------------------
# simulate_pnl — bull put
# ---------------------------------------------------------------------------


class TestSimulatePnlBullPut:
    def test_full_profit_above_short_strike(self) -> None:
        rec = make_bull_put(short=5200.0, long=5195.0, credit=150.0)
        assert simulate_pnl(rec, 5300.0) == pytest.approx(150.0)

    def test_full_loss_below_long_strike(self) -> None:
        rec = make_bull_put(short=5200.0, long=5195.0, credit=150.0)
        # short_value = (5200-5190)*100=1000, long_value = (5195-5190)*100=500
        # pnl = 150 - 1000 + 500 = -350
        assert simulate_pnl(rec, 5190.0) == pytest.approx(-350.0)

    def test_partial_loss_between_strikes(self) -> None:
        rec = make_bull_put(short=5200.0, long=5195.0, credit=150.0)
        # expiry=5198: short_value=(5200-5198)*100=200, long_value=0
        # pnl = 150 - 200 + 0 = -50
        assert simulate_pnl(rec, 5198.0) == pytest.approx(-50.0)

    def test_exactly_at_short_strike_is_full_profit(self) -> None:
        rec = make_bull_put(short=5200.0, long=5195.0, credit=150.0)
        assert simulate_pnl(rec, 5200.0) == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# simulate_pnl — bear call
# ---------------------------------------------------------------------------


class TestSimulatePnlBearCall:
    def test_full_profit_below_short_strike(self) -> None:
        rec = make_bear_call(short=5300.0, long=5305.0, credit=150.0)
        assert simulate_pnl(rec, 5200.0) == pytest.approx(150.0)

    def test_full_loss_above_long_strike(self) -> None:
        rec = make_bear_call(short=5300.0, long=5305.0, credit=150.0)
        # short_value=(5310-5300)*100=1000, long_value=(5310-5305)*100=500
        # pnl = 150 - 1000 + 500 = -350
        assert simulate_pnl(rec, 5310.0) == pytest.approx(-350.0)

    def test_partial_loss_between_strikes(self) -> None:
        rec = make_bear_call(short=5300.0, long=5305.0, credit=150.0)
        # expiry=5302: short_value=(5302-5300)*100=200, long_value=0
        # pnl = 150 - 200 + 0 = -50
        assert simulate_pnl(rec, 5302.0) == pytest.approx(-50.0)

    def test_exactly_at_short_strike_is_full_profit(self) -> None:
        rec = make_bear_call(short=5300.0, long=5305.0, credit=150.0)
        assert simulate_pnl(rec, 5300.0) == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# BacktestResult properties
# ---------------------------------------------------------------------------


class TestBacktestResult:
    def test_total_trades(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(-350.0), make_trade(150.0)],
        )
        assert result.total_trades == 3

    def test_winning_trades(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(-350.0), make_trade(150.0)],
        )
        assert result.winning_trades == 2

    def test_losing_trades(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(-350.0), make_trade(150.0)],
        )
        assert result.losing_trades == 1

    def test_win_rate(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(-350.0), make_trade(150.0)],
        )
        assert result.win_rate == pytest.approx(2 / 3)

    def test_total_pnl(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(-350.0), make_trade(150.0)],
        )
        assert result.total_pnl == pytest.approx(-50.0)

    def test_average_credit(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(100.0, credit=100.0), make_trade(200.0, credit=200.0)],
        )
        assert result.average_credit == pytest.approx(150.0)

    def test_average_pnl(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(100.0), make_trade(-200.0)],
        )
        assert result.average_pnl == pytest.approx(-50.0)

    def test_max_drawdown_with_loss(self) -> None:
        # cumulative: 150, -200, -50 → peak=150, trough=-200, dd=350
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(-350.0), make_trade(150.0)],
        )
        assert result.max_drawdown == pytest.approx(350.0)

    def test_max_drawdown_all_winners(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(150.0)],
        )
        assert result.max_drawdown == pytest.approx(0.0)

    def test_empty_result(self) -> None:
        result = BacktestResult(config=make_config(), trades=[])
        assert result.total_trades == 0
        assert result.win_rate == pytest.approx(0.0)
        assert result.total_pnl == pytest.approx(0.0)
        assert result.max_drawdown == pytest.approx(0.0)

    def test_open_trades_excluded_from_win_rate(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(None)],
        )
        assert result.win_rate == pytest.approx(1.0)

    def test_open_trades_excluded_from_total_pnl(self) -> None:
        result = BacktestResult(
            config=make_config(),
            trades=[make_trade(150.0), make_trade(None)],
        )
        assert result.total_pnl == pytest.approx(150.0)

    def test_average_credit_zero_when_no_trades(self) -> None:
        result = BacktestResult(config=make_config(), trades=[])
        assert result.average_credit == pytest.approx(0.0)

    def test_average_pnl_zero_when_no_completed_trades(self) -> None:
        result = BacktestResult(config=make_config(), trades=[make_trade(None)])
        assert result.average_pnl == pytest.approx(0.0)
