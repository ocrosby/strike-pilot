"""Unit tests for YFinanceMarketDataAdapter.

All yfinance network calls are mocked — tests verify adapter logic only.
"""

from __future__ import annotations

import pandas as pd
import pytest

from strike_pilot.adapters.yfinance_market_data import (
    YFinanceMarketDataAdapter,
    _compute_iv_percentile,
    _compute_iv_rank,
)
from strike_pilot.domain.models import MarketSnapshot
from strike_pilot.ports.interfaces import MarketDataProvider


def _make_vix_series(values: list[float]) -> pd.Series:
    """Build a VIX pd.Series from a list of float values."""
    dates = pd.date_range(end="2024-01-19", periods=len(values), freq="B")
    return pd.Series(values, index=dates, name="Close")


def _make_price_df(n: int = 60, base: float = 5250.0) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with n rows for mocking history()."""
    dates = pd.date_range(end="2024-01-19", periods=n, freq="B")
    closes = [base + i * 0.5 for i in range(n)]
    return pd.DataFrame(
        {
            "Open": [c - 5.0 for c in closes],
            "High": [c + 8.0 for c in closes],
            "Low": [c - 8.0 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * n,
        },
        index=dates,
    )


def _make_vix_df() -> pd.DataFrame:
    """Build a single-row VIX history DataFrame."""
    dates = pd.date_range(end="2024-01-19", periods=1, freq="B")
    return pd.DataFrame(
        {"Open": [16.0], "High": [17.0], "Low": [15.5], "Close": [16.5], "Volume": [0]},
        index=dates,
    )


class TestYFinanceMarketDataAdapter:
    def test_implements_market_data_provider(self) -> None:
        adapter = YFinanceMarketDataAdapter()
        assert isinstance(adapter, MarketDataProvider)

    def test_returns_market_snapshot(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        assert isinstance(result, MarketSnapshot)

    def test_symbol_preserved_in_snapshot(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        assert result.symbol == "SPX"

    def test_price_is_latest_close(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df(n=60, base=5000.0)
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        expected_close = float(price_df["Close"].iloc[-1])
        assert result.price == pytest.approx(expected_close)

    def test_ohlc_fields_populated(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        assert result.open_price == pytest.approx(float(price_df["Open"].iloc[-1]))
        assert result.high_price == pytest.approx(float(price_df["High"].iloc[-1]))
        assert result.low_price == pytest.approx(float(price_df["Low"].iloc[-1]))

    def test_vix_comes_from_vix_ticker(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        assert result.vix == pytest.approx(16.5)

    def test_sma_20_computed_from_last_20_closes(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        expected = float(price_df["Close"].tail(20).mean())
        assert result.sma_20 == pytest.approx(expected)

    def test_sma_50_computed_from_last_50_closes(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        expected = float(price_df["Close"].tail(50).mean())
        assert result.sma_50 == pytest.approx(expected)

    def test_rsi_14_within_valid_range(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        assert 0.0 <= result.rsi_14 <= 100.0

    def test_spx_symbol_prefixed_with_caret(self, mocker: pytest.MonkeyPatch) -> None:
        """Adapter must request ^SPX from yfinance, not bare SPX."""
        price_df = _make_price_df()
        vix_df = _make_vix_df()
        called_with: list[str] = []

        def ticker_factory(symbol: str) -> object:
            called_with.append(symbol)
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        adapter.get_snapshot("SPX")

        assert "^SPX" in called_with

    def test_raises_on_empty_history(self, mocker: pytest.MonkeyPatch) -> None:
        empty_df = pd.DataFrame()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = empty_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        with pytest.raises(ValueError, match="No data available"):
            adapter.get_snapshot("SPX")

    def test_non_index_symbol_not_prefixed(self, mocker: pytest.MonkeyPatch) -> None:
        """Equity symbols (e.g. AAPL) must be passed to yfinance unchanged."""
        price_df = _make_price_df()
        vix_df = _make_vix_df()
        called_with: list[str] = []

        def ticker_factory(symbol: str) -> object:
            called_with.append(symbol)
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        adapter.get_snapshot("AAPL")

        assert "AAPL" in called_with
        assert "^AAPL" not in called_with

    def test_rsi_normal_path_with_mixed_price_changes(self, mocker: pytest.MonkeyPatch) -> None:
        """RSI must be < 100 when there are losing days (avg_loss != 0)."""
        # Alternating up/down days ensure avg_loss != 0, exercising the normal RSI formula.
        closes = [5200.0 + (1.0 if i % 2 == 0 else -0.5) * i for i in range(60)]
        dates = pd.date_range(end="2024-01-19", periods=60, freq="B")
        price_df = pd.DataFrame(
            {
                "Open": [c - 2.0 for c in closes],
                "High": [c + 3.0 for c in closes],
                "Low": [c - 3.0 for c in closes],
                "Close": closes,
                "Volume": [1_000_000] * 60,
            },
            index=dates,
        )
        vix_df = _make_vix_df()

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        adapter = YFinanceMarketDataAdapter()
        result = adapter.get_snapshot("SPX")

        assert 0.0 < result.rsi_14 < 100.0


class TestComputeIvRank:
    def test_returns_zero_when_all_values_equal(self) -> None:
        series = _make_vix_series([15.0] * 252)
        assert _compute_iv_rank(series) == pytest.approx(0.0)

    def test_returns_one_when_current_is_at_max(self) -> None:
        # Current (last) value is the 52w high
        values = [10.0] * 251 + [30.0]
        series = _make_vix_series(values)
        assert _compute_iv_rank(series) == pytest.approx(1.0)

    def test_returns_zero_when_current_is_at_min(self) -> None:
        # Current (last) value is the 52w low
        values = [30.0] * 251 + [10.0]
        series = _make_vix_series(values)
        assert _compute_iv_rank(series) == pytest.approx(0.0)

    def test_returns_half_when_current_is_midpoint(self) -> None:
        # Range 10-30, current = 20
        values = [10.0] * 125 + [30.0] * 126 + [20.0]
        series = _make_vix_series(values)
        assert _compute_iv_rank(series) == pytest.approx(0.5)

    def test_result_clamped_between_zero_and_one(self) -> None:
        values = list(range(1, 253))  # 1 to 252
        series = _make_vix_series([float(v) for v in values])
        rank = _compute_iv_rank(series)
        assert 0.0 <= rank <= 1.0


class TestComputeIvPercentile:
    def test_returns_zero_when_current_is_minimum(self) -> None:
        # Current is 5.0, all others are 20.0 — no days below current
        values = [20.0] * 251 + [5.0]
        series = _make_vix_series(values)
        assert _compute_iv_percentile(series) == pytest.approx(0.0)

    def test_returns_one_when_current_is_maximum(self) -> None:
        # Current is 30.0, all others are 10.0 — all days below current
        values = [10.0] * 251 + [30.0]
        series = _make_vix_series(values)
        assert _compute_iv_percentile(series) == pytest.approx(1.0)

    def test_returns_half_when_half_of_days_are_below_current(self) -> None:
        # 125 days at 10.0, 125 days at 30.0, current at 20.0
        # 125 out of 250 historical days are below 20.0 → 0.5
        values = [10.0] * 125 + [30.0] * 125 + [20.0]
        series = _make_vix_series(values)
        assert _compute_iv_percentile(series) == pytest.approx(0.5)

    def test_result_between_zero_and_one(self) -> None:
        values = list(range(1, 253))
        series = _make_vix_series([float(v) for v in values])
        pct = _compute_iv_percentile(series)
        assert 0.0 <= pct <= 1.0


class TestIvRankAndPercentileInSnapshot:
    def test_iv_rank_populated_in_snapshot(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        # Varying VIX: low=10, high=30, current=20 → iv_rank ≈ 0.5
        vix_values = [10.0] * 125 + [30.0] * 126 + [20.0]
        vix_df = pd.DataFrame(
            {
                "Open": vix_values,
                "High": vix_values,
                "Low": vix_values,
                "Close": vix_values,
                "Volume": [0] * len(vix_values),
            },
            index=pd.date_range(end="2024-01-19", periods=len(vix_values), freq="B"),
        )

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        result = YFinanceMarketDataAdapter().get_snapshot("SPX")

        assert result.iv_rank is not None
        assert 0.0 <= result.iv_rank <= 1.0

    def test_iv_percentile_populated_in_snapshot(self, mocker: pytest.MonkeyPatch) -> None:
        price_df = _make_price_df()
        vix_values = [10.0] * 125 + [30.0] * 126 + [20.0]
        vix_df = pd.DataFrame(
            {
                "Open": vix_values,
                "High": vix_values,
                "Low": vix_values,
                "Close": vix_values,
                "Volume": [0] * len(vix_values),
            },
            index=pd.date_range(end="2024-01-19", periods=len(vix_values), freq="B"),
        )

        def ticker_factory(symbol: str) -> object:
            mock = mocker.MagicMock()
            mock.history.return_value = vix_df if symbol == "^VIX" else price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        result = YFinanceMarketDataAdapter().get_snapshot("SPX")

        assert result.iv_percentile is not None
        assert 0.0 <= result.iv_percentile <= 1.0

    def test_vix_fetched_with_one_year_period(self, mocker: pytest.MonkeyPatch) -> None:
        """Adapter must request 1y of VIX history to support iv_rank computation."""
        price_df = _make_price_df()
        vix_df = _make_vix_df()
        vix_ticker = mocker.MagicMock()
        vix_ticker.history.return_value = vix_df

        def ticker_factory(symbol: str) -> object:
            if symbol == "^VIX":
                return vix_ticker
            mock = mocker.MagicMock()
            mock.history.return_value = price_df
            return mock

        mocker.patch(
            "strike_pilot.adapters.yfinance_market_data.yf.Ticker", side_effect=ticker_factory
        )

        YFinanceMarketDataAdapter().get_snapshot("SPX")

        vix_ticker.history.assert_called_once_with(period="1y")
