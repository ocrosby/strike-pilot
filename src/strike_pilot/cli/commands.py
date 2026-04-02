"""CLI command definitions for Strike Pilot.

Commands are thin wrappers that wire dependencies and delegate
all business logic to the application use cases.
No business logic should appear here.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from strike_pilot.adapters.alert import ConsoleAlertService
from strike_pilot.adapters.clock import SystemClock
from strike_pilot.adapters.csv_logger import CsvRecommendationLogger
from strike_pilot.adapters.market_data import StaticMarketDataAdapter
from strike_pilot.adapters.options_chain import StaticOptionsChainAdapter
from strike_pilot.adapters.presenters import ConsolePresenter, JsonPresenter
from strike_pilot.adapters.yfinance_market_data import YFinanceMarketDataAdapter
from strike_pilot.application.use_cases import AnalyzeAndRecommendUseCase
from strike_pilot.domain.models import ExpiryCategory, RiskParameters
from strike_pilot.domain.services import (
    DeltaBasedStrikeSelector,
    ProbabilityOfProfitStrikeSelector,
    RiskRewardStrikeSelector,
    SimpleMomentumBiasStrategy,
    StrikeSelectionStrategy,
)


@click.group()
@click.version_option()
def cli() -> None:
    """Strike Pilot: SPX intraday bias and credit spread recommendation engine."""


@cli.command("analyze")
@click.option(
    "--symbol",
    default="SPX",
    show_default=True,
    help="Market symbol to analyze.",
)
@click.option(
    "--expiry",
    default=None,
    help="Explicit expiry date (YYYY-MM-DD). Overrides --expiry-type.",
)
@click.option(
    "--expiry-type",
    "expiry_types",
    multiple=True,
    type=click.Choice(["0dte", "weekly", "monthly"], case_sensitive=False),
    help="Expiry categories to analyze (repeatable). Defaults to weekly.",
)
@click.option(
    "--max-loss",
    default=1000.0,
    show_default=True,
    type=float,
    help="Maximum acceptable loss in dollars.",
)
@click.option(
    "--min-credit",
    default=50.0,
    show_default=True,
    type=float,
    help="Minimum acceptable net credit in dollars.",
)
@click.option(
    "--spread-width",
    default=10.0,
    show_default=True,
    type=float,
    help="Maximum spread width in points.",
)
@click.option(
    "--min-confidence",
    default=0.6,
    show_default=True,
    type=float,
    help="Minimum confidence threshold (0.0-1.0).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "json"], case_sensitive=False),
    default="console",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--log-csv",
    "log_csv",
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help="Path to a CSV file for logging recommendations.",
)
@click.option(
    "--data-source",
    "data_source",
    type=click.Choice(["static", "live"], case_sensitive=False),
    default="static",
    show_default=True,
    help="Market data source: 'static' for hardcoded demo data, 'live' for Yahoo Finance.",
)
@click.option(
    "--strategy",
    "strategy",
    type=click.Choice(["delta", "pop", "risk-reward"], case_sensitive=False),
    default="delta",
    show_default=True,
    help="Strike selection strategy: delta targeting, probability of profit, or R/R targeting.",
)
@click.option(
    "--target-pop",
    "target_pop",
    default=0.80,
    show_default=True,
    type=float,
    help="Target probability of profit (0.0-1.0). Used when --strategy=pop.",
)
@click.option(
    "--target-rr",
    "target_rr",
    default=5.0,
    show_default=True,
    type=float,
    help="Target risk-reward ratio (e.g. 5.0 means 5:1). Used when --strategy=risk-reward.",
)
@click.option(
    "--alert",
    "alert",
    is_flag=True,
    default=False,
    help="Print a trade alert to the console when a spread is recommended.",
)
def analyze_command(
    symbol: str,
    expiry: str | None,
    expiry_types: tuple[str, ...],
    max_loss: float,
    min_credit: float,
    spread_width: float,
    min_confidence: float,
    output_format: str,
    log_csv: str | None,
    data_source: str,
    strategy: str,
    target_pop: float,
    target_rr: float,
    alert: bool,
) -> None:
    """Analyze SPX intraday bias and generate credit spread recommendations."""
    risk_params = RiskParameters(
        max_loss_dollars=max_loss,
        min_credit_dollars=min_credit,
        max_spread_width=spread_width,
        min_confidence_threshold=min_confidence,
    )

    presenter = JsonPresenter() if output_format == "json" else ConsolePresenter()
    logger = CsvRecommendationLogger(Path(log_csv)) if log_csv else None
    market_data = (
        YFinanceMarketDataAdapter() if data_source == "live" else StaticMarketDataAdapter()
    )

    strike_selector: StrikeSelectionStrategy
    if strategy == "pop":
        strike_selector = ProbabilityOfProfitStrikeSelector(
            target_pop=target_pop,
            spread_width=spread_width,
        )
    elif strategy == "risk-reward":
        strike_selector = RiskRewardStrikeSelector(
            target_rr_ratio=target_rr,
            max_spread_width=spread_width,
        )
    else:
        strike_selector = DeltaBasedStrikeSelector(
            target_short_delta=0.20,
            spread_width=spread_width,
        )

    use_case = AnalyzeAndRecommendUseCase(
        market_data_provider=market_data,
        options_chain_provider=StaticOptionsChainAdapter(),
        bias_strategy=SimpleMomentumBiasStrategy(),
        strike_selector=strike_selector,
        presenter=presenter,
        clock=SystemClock(),
        logger=logger,
        alert_service=ConsoleAlertService() if alert else None,
    )

    if expiry:
        use_case.execute(symbol=symbol, risk_params=risk_params, expiry=expiry)
    else:
        categories = [ExpiryCategory(t) for t in expiry_types] if expiry_types else None
        use_case.execute_multi(symbol=symbol, risk_params=risk_params, categories=categories)


@cli.command("backtest")
@click.option("--symbol", default="SPX", show_default=True, help="Market symbol to backtest.")
@click.option("--start", "start_date", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--end", "end_date", required=True, help="End date (YYYY-MM-DD).")
@click.option(
    "--max-loss", default=1000.0, show_default=True, type=float, help="Max loss in dollars."
)
@click.option(
    "--min-credit", default=50.0, show_default=True, type=float, help="Min net credit in dollars."
)
@click.option(
    "--spread-width", default=10.0, show_default=True, type=float, help="Spread width in points."
)
@click.option(
    "--min-confidence", default=0.6, show_default=True, type=float, help="Min confidence threshold."
)
@click.option(
    "--data-source",
    "data_source",
    type=click.Choice(["static", "live"], case_sensitive=False),
    default="static",
    show_default=True,
    help="Historical data source.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "json"], case_sensitive=False),
    default="console",
    show_default=True,
    help="Output format.",
)
def backtest_command(
    symbol: str,
    start_date: str,
    end_date: str,
    max_loss: float,
    min_credit: float,
    spread_width: float,
    min_confidence: float,
    data_source: str,
    output_format: str,
) -> None:
    """Backtest the recommendation engine over a historical date range."""
    from strike_pilot.adapters.static_historical import StaticHistoricalDataAdapter
    from strike_pilot.adapters.synthetic_chain import SyntheticOptionsChainAdapter
    from strike_pilot.application.backtest import RunBacktestUseCase
    from strike_pilot.domain.backtest import BacktestConfig

    risk_params = RiskParameters(
        max_loss_dollars=max_loss,
        min_credit_dollars=min_credit,
        max_spread_width=spread_width,
        min_confidence_threshold=min_confidence,
    )

    if data_source == "live":
        from strike_pilot.adapters.yfinance_historical import YFinanceHistoricalDataAdapter

        historical: object = YFinanceHistoricalDataAdapter()
    else:
        historical = StaticHistoricalDataAdapter()

    config = BacktestConfig(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        risk_params=risk_params,
        spread_width=spread_width,
    )

    use_case = RunBacktestUseCase(
        historical_data=historical,  # type: ignore[arg-type]
        bias_strategy=SimpleMomentumBiasStrategy(),
        chain_factory=lambda snap: SyntheticOptionsChainAdapter(snap, strike_step=spread_width),
        strike_selector=DeltaBasedStrikeSelector(
            target_short_delta=0.20,
            spread_width=spread_width,
        ),
    )

    result = use_case.execute(config)

    if output_format == "json":
        click.echo(
            json.dumps(
                {
                    "symbol": result.config.symbol,
                    "start_date": result.config.start_date,
                    "end_date": result.config.end_date,
                    "total_trades": result.total_trades,
                    "winning_trades": result.winning_trades,
                    "losing_trades": result.losing_trades,
                    "win_rate": round(result.win_rate, 4),
                    "total_pnl": round(result.total_pnl, 2),
                    "average_credit": round(result.average_credit, 2),
                    "average_pnl": round(result.average_pnl, 2),
                    "max_drawdown": round(result.max_drawdown, 2),
                    "trades": [
                        {
                            "entry_date": t.entry_date,
                            "expiry_date": t.expiry_date,
                            "spread_type": t.spread_type,
                            "short_strike": t.short_strike,
                            "long_strike": t.long_strike,
                            "net_credit": t.net_credit,
                            "max_loss": t.max_loss,
                            "expiry_close": t.expiry_close,
                            "pnl": t.pnl,
                        }
                        for t in result.trades
                    ],
                },
                indent=2,
            )
        )
    else:
        sep = "=" * 50
        click.echo(sep)
        click.echo("BACKTEST RESULTS")
        click.echo(sep)
        click.echo(f"  Symbol       : {result.config.symbol}")
        click.echo(f"  Period       : {result.config.start_date} to {result.config.end_date}")
        click.echo(sep)
        click.echo(f"  Total Trades : {result.total_trades}")
        click.echo(f"  Winning      : {result.winning_trades}")
        click.echo(f"  Losing       : {result.losing_trades}")
        if result.total_trades:
            click.echo(f"  Win Rate     : {result.win_rate:.1%}")
        click.echo(sep)
        click.echo(f"  Total P&L    : ${result.total_pnl:,.2f}")
        click.echo(f"  Avg Credit   : ${result.average_credit:,.2f}")
        click.echo(f"  Avg P&L      : ${result.average_pnl:,.2f}")
        click.echo(f"  Max Drawdown : ${result.max_drawdown:,.2f}")
        click.echo(sep)


@cli.command("serve")
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host address to bind the API server.",
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Port number to listen on.",
)
def serve_command(host: str, port: int) -> None:
    """Start the Strike Pilot HTTP API server."""
    import uvicorn

    from strike_pilot.adapters.api.app import create_app

    uvicorn.run(create_app(), host=host, port=port)
