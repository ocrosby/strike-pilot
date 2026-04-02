"""Unit tests for RunBacktestUseCase."""

from __future__ import annotations

from unittest.mock import MagicMock

from strike_pilot.adapters.options_chain import StaticOptionsChainAdapter
from strike_pilot.adapters.static_historical import StaticHistoricalDataAdapter
from strike_pilot.application.backtest import RunBacktestUseCase
from strike_pilot.domain.backtest import BacktestConfig, BacktestResult, TradeRecord
from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    MarketSnapshot,
    NoTradeSignal,
    RiskParameters,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)


def make_config(
    start: str = "2024-01-15",
    end: str = "2024-01-19",
) -> BacktestConfig:
    return BacktestConfig(
        symbol="SPX",
        start_date=start,
        end_date=end,
        risk_params=RiskParameters(
            max_loss_dollars=1000.0,
            min_credit_dollars=10.0,
            max_spread_width=50.0,
            min_confidence_threshold=0.1,
        ),
    )


def make_bullish_bias() -> MarketBias:
    return MarketBias(direction=BiasDirection.BULLISH, confidence=ConfidenceScore(0.8))


def make_recommendation() -> SpreadRecommendation:
    bias = make_bullish_bias()
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
    )


def make_use_case(
    snapshots: list[MarketSnapshot] | None = None,
    close_prices: dict[str, float] | None = None,
    bias: MarketBias | None = None,
    recommendation: SpreadRecommendation | NoTradeSignal | None = None,
) -> RunBacktestUseCase:
    historical_data = MagicMock()
    historical_data.get_snapshots.return_value = (
        snapshots
        if snapshots is not None
        else StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-19")
    )
    default_prices = {"2024-01-19": 5260.0, "2024-01-26": 5270.0}
    prices = close_prices if close_prices is not None else default_prices
    historical_data.get_close_price.side_effect = lambda sym, date: prices.get(date)

    bias_strategy = MagicMock()
    bias_strategy.analyze.return_value = bias or make_bullish_bias()

    chain_factory = lambda snap: StaticOptionsChainAdapter()  # noqa: E731

    strike_selector = MagicMock()
    strike_selector.select_strikes.return_value = recommendation or make_recommendation()

    return RunBacktestUseCase(
        historical_data=historical_data,
        bias_strategy=bias_strategy,
        chain_factory=chain_factory,
        strike_selector=strike_selector,
    )


class TestRunBacktestUseCase:
    def test_returns_backtest_result(self) -> None:
        use_case = make_use_case()
        result = use_case.execute(make_config())
        assert isinstance(result, BacktestResult)

    def test_config_preserved_in_result(self) -> None:
        config = make_config()
        use_case = make_use_case()
        result = use_case.execute(config)
        assert result.config is config

    def test_records_trade_when_spread_recommended(self) -> None:
        snapshot = StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-15")
        use_case = make_use_case(snapshots=snapshot)
        result = use_case.execute(make_config())
        assert len(result.trades) == 1
        assert isinstance(result.trades[0], TradeRecord)

    def test_no_trade_recorded_for_no_trade_signal(self) -> None:
        snapshot = StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-15")
        no_trade = NoTradeSignal(reason="Neutral", bias=make_bullish_bias())
        use_case = make_use_case(snapshots=snapshot, recommendation=no_trade)
        result = use_case.execute(make_config())
        assert len(result.trades) == 0

    def test_pnl_computed_from_expiry_close(self) -> None:
        snapshot = StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-15")
        # expiry close 5300 >> short strike 5200 → full profit = 150
        use_case = make_use_case(snapshots=snapshot, close_prices={"2024-01-19": 5300.0})
        result = use_case.execute(make_config())
        assert len(result.trades) == 1
        assert result.trades[0].pnl == 150.0

    def test_pnl_is_none_when_expiry_close_unavailable(self) -> None:
        snapshot = StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-15")
        use_case = make_use_case(snapshots=snapshot, close_prices={})
        result = use_case.execute(make_config())
        assert result.trades[0].pnl is None

    def test_multiple_snapshots_produce_multiple_trades(self) -> None:
        snapshots = StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-19")
        assert len(snapshots) > 1
        prices = {"2024-01-19": 5300.0, "2024-01-26": 5310.0}
        use_case = make_use_case(snapshots=snapshots, close_prices=prices)
        result = use_case.execute(make_config())
        assert result.total_trades == len(snapshots)

    def test_trade_entry_date_matches_snapshot_date(self) -> None:
        snapshot = StaticHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-15")
        use_case = make_use_case(snapshots=snapshot)
        result = use_case.execute(make_config())
        assert result.trades[0].entry_date == "2024-01-15"

    def test_empty_snapshot_range_produces_no_trades(self) -> None:
        use_case = make_use_case(snapshots=[])
        result = use_case.execute(make_config())
        assert result.total_trades == 0
