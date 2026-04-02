"""CLI command definitions for Strike Pilot.

Commands are thin wrappers that wire dependencies and delegate
all business logic to the application use cases.
No business logic should appear here.
"""

from __future__ import annotations

from pathlib import Path

import click

from strike_pilot.adapters.clock import SystemClock
from strike_pilot.adapters.csv_logger import CsvRecommendationLogger
from strike_pilot.adapters.market_data import StaticMarketDataAdapter
from strike_pilot.adapters.options_chain import StaticOptionsChainAdapter
from strike_pilot.adapters.presenters import ConsolePresenter, JsonPresenter
from strike_pilot.adapters.yfinance_market_data import YFinanceMarketDataAdapter
from strike_pilot.application.use_cases import AnalyzeAndRecommendUseCase
from strike_pilot.domain.models import ExpiryCategory, RiskParameters
from strike_pilot.domain.services import DeltaBasedStrikeSelector, SimpleMomentumBiasStrategy


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

    use_case = AnalyzeAndRecommendUseCase(
        market_data_provider=market_data,
        options_chain_provider=StaticOptionsChainAdapter(),
        bias_strategy=SimpleMomentumBiasStrategy(),
        strike_selector=DeltaBasedStrikeSelector(
            target_short_delta=0.20,
            spread_width=spread_width,
        ),
        presenter=presenter,
        clock=SystemClock(),
        logger=logger,
    )

    if expiry:
        use_case.execute(symbol=symbol, risk_params=risk_params, expiry=expiry)
    else:
        categories = [ExpiryCategory(t) for t in expiry_types] if expiry_types else None
        use_case.execute_multi(symbol=symbol, risk_params=risk_params, categories=categories)
