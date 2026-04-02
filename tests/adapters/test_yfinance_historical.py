"""Unit tests for YFinanceHistoricalDataAdapter.

All yfinance network calls are mocked — tests verify adapter logic only.
"""

from __future__ import annotations

import pandas as pd
import pytest

from strike_pilot.adapters.yfinance_historical import YFinanceHistoricalDataAdapter
from strike_pilot.domain.models import MarketSnapshot
from strike_pilot.ports.interfaces import HistoricalDataProvider


def _make_history_df(start: str = "2023-09-01", periods: int = 130) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with mixed up/down closes for realistic RSI."""
    dates = pd.date_range(start, periods=periods, freq="B")
    # Alternate slight up and down days so avg_loss != 0 and RSI is in (0, 100)
    closes = [5200.0 + (1.0 if i % 3 != 2 else -0.5) * i for i in range(periods)]
    return pd.DataFrame(
        {
            "Open": [c - 2.0 for c in closes],
            "High": [c + 4.0 for c in closes],
            "Low": [c - 4.0 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * periods,
        },
        index=dates,
    )


def _make_vix_df(
    start: str = "2023-09-01", periods: int = 130, level: float = 16.0
) -> pd.DataFrame:
    """Build a flat VIX history DataFrame."""
    dates = pd.date_range(start, periods=periods, freq="B")
    return pd.DataFrame(
        {
            "Open": [level] * periods,
            "High": [level + 1.0] * periods,
            "Low": [level - 1.0] * periods,
            "Close": [level] * periods,
            "Volume": [0] * periods,
        },
        index=dates,
    )


class TestYFinanceHistoricalDataAdapter:
    def test_implements_historical_data_provider(self) -> None:
        assert isinstance(YFinanceHistoricalDataAdapter(), HistoricalDataProvider)

    def test_get_snapshots_returns_list_of_market_snapshots(
        self, mocker: pytest.MonkeyPatch
    ) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        # Use indices near the end so we're past the warmup prefix
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        assert len(snapshots) > 0
        assert all(isinstance(s, MarketSnapshot) for s in snapshots)

    def test_get_snapshots_excludes_warmup_rows(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        for s in snapshots:
            assert start_date <= s.timestamp[:10] <= end_date

    def test_get_snapshots_symbol_preserved(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        assert all(s.symbol == "SPX" for s in snapshots)

    def test_get_snapshots_vix_populated_from_vix_history(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df(level=18.0)
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        assert all(s.vix == pytest.approx(18.0) for s in snapshots)

    def test_get_snapshots_vix_defaults_to_20_when_vix_data_empty(
        self, mocker: pytest.MonkeyPatch
    ) -> None:
        history = _make_history_df()
        empty_vix = pd.DataFrame(
            {"Open": [], "High": [], "Low": [], "Close": [], "Volume": []},
            index=pd.DatetimeIndex([], dtype="datetime64[ns]"),
        )
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, empty_vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        assert all(s.vix == pytest.approx(20.0) for s in snapshots)

    def test_get_snapshots_returns_empty_when_history_empty(
        self, mocker: pytest.MonkeyPatch
    ) -> None:
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[pd.DataFrame(), pd.DataFrame()],
        )

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", "2024-01-15", "2024-01-19")

        assert snapshots == []

    def test_get_snapshots_sma_fields_populated(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        for s in snapshots:
            assert s.sma_20 > 0.0
            assert s.sma_50 > 0.0

    def test_get_snapshots_rsi_within_valid_range(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        for s in snapshots:
            assert 0.0 <= s.rsi_14 <= 100.0

    def test_get_close_price_returns_float(self, mocker: pytest.MonkeyPatch) -> None:
        df = pd.DataFrame(
            {"Close": [5280.0]},
            index=pd.date_range("2024-01-19", periods=1, freq="B"),
        )
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            return_value=df,
        )

        price = YFinanceHistoricalDataAdapter().get_close_price("SPX", "2024-01-19")

        assert price == pytest.approx(5280.0)

    def test_get_close_price_returns_none_when_empty(self, mocker: pytest.MonkeyPatch) -> None:
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            return_value=pd.DataFrame(),
        )

        price = YFinanceHistoricalDataAdapter().get_close_price("SPX", "2024-01-20")

        assert price is None

    def test_iv_rank_populated_in_snapshots(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        for s in snapshots:
            assert s.iv_rank is not None
            assert 0.0 <= s.iv_rank <= 1.0

    def test_iv_percentile_populated_in_snapshots(self, mocker: pytest.MonkeyPatch) -> None:
        history = _make_history_df()
        vix = _make_vix_df()
        mocker.patch(
            "strike_pilot.adapters.yfinance_historical.yf.download",
            side_effect=[history, vix],
        )
        start_date = history.index[100].strftime("%Y-%m-%d")
        end_date = history.index[-1].strftime("%Y-%m-%d")

        snapshots = YFinanceHistoricalDataAdapter().get_snapshots("SPX", start_date, end_date)

        for s in snapshots:
            assert s.iv_percentile is not None
            assert 0.0 <= s.iv_percentile <= 1.0
