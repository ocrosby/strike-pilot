# Strike Pilot

> **SPX intraday bias and credit spread recommendation engine**

[![CI](https://github.com/ocrosby/strike-pilot/actions/workflows/ci.yml/badge.svg)](https://github.com/ocrosby/strike-pilot/actions/workflows/ci.yml)

---

## What is Strike Pilot?

Strike Pilot is a Python-based analysis engine that:

1. **Ingests** intraday market signals for SPX (price action, RSI, SMA, VIX).
2. **Determines** a directional bias (bullish, bearish, or neutral) with a calibrated confidence score.
3. **Recommends** a credit spread (bull put or bear call) — or signals *no trade* — based on configurable risk constraints.

---

## The Problem

Retail options traders often make discretionary credit spread decisions without a consistent, repeatable framework. Without systematic signal aggregation and risk validation, trades can be taken with insufficient conviction, inappropriate strike placement, or violated risk parameters.

---

## The Solution

Strike Pilot provides a clean, extensible architecture that:

- Aggregates momentum signals into a directional bias score.
- Applies configurable strike selection strategies (delta targeting, probability of profit, risk-reward) to select spread strikes.
- Validates every candidate trade against configurable risk parameters before recommending it.
- Presents results in human-readable or machine-readable (JSON) format.
- Logs recommendations to CSV for later analysis.
- Fires configurable alerts (console, logging) when a spread is recommended.
- Backtests the full strategy over historical data using real or synthetic options chains.
- Exposes all functionality via an HTTP API (FastAPI) in addition to the CLI.

The architecture is deliberately designed for **replaceability**: swap in live market data, alternative bias strategies, new alert channels, or different output formats without touching the core domain logic.

---

## Architecture

Strike Pilot follows a pragmatic **Ports and Adapters (Hexagonal)** architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI (inbound adapter)          HTTP API (inbound adapter)      │
│  click commands                 FastAPI / uvicorn               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Application Layer                                              │
│  AnalyzeAndRecommendUseCase   RunBacktestUseCase                │
└──────┬───────────────────────────────────────────────────┬──────┘
       │ depends on ports (Protocols)                      │
┌──────▼──────────┐                          ┌─────────────▼──────┐
│  Domain Layer   │                          │  Adapters Layer    │
│  models         │                          │  StaticMarketData  │
│  policies       │                          │  YFinanceMarketData│
│  services       │                          │  StaticOptionsChain│
│  backtest       │                          │  SyntheticChain    │
│  BiasStrategy   │                          │  StaticHistorical  │
│  StrikeSelector │                          │  YFinanceHistorical│
│                 │                          │  ConsolePresenter  │
│                 │                          │  JsonPresenter     │
│                 │                          │  SystemClock       │
│                 │                          │  CsvLogger         │
│                 │                          │  AlertService      │
└─────────────────┘                          └────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| `domain` | Pure Python models and business rules — zero I/O dependencies |
| `ports` | `Protocol`-based interfaces — contracts between layers |
| `adapters` | Concrete implementations: static/live data, presenters, API, alerting |
| `application` | Orchestrates domain + adapters to execute use cases |
| `cli` | Wires dependencies, delegates to use cases, no business logic |

---

## Project Structure

```
strike-pilot/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI pipeline
├── src/
│   └── strike_pilot/
│       ├── domain/
│       │   ├── models.py       # MarketBias, SpreadRecommendation, RiskParameters…
│       │   ├── policies.py     # Risk validation rules (pure functions)
│       │   ├── services.py     # BiasStrategy, StrikeSelectionStrategy, implementations
│       │   ├── backtest.py     # BacktestConfig, BacktestResult, TradeRecord, simulate_pnl
│       │   ├── expiry.py       # weekly_expiry, expiry date helpers
│       │   └── iv.py           # IV rank / IV percentile helpers
│       ├── ports/
│       │   └── interfaces.py   # Protocol interfaces for all boundaries
│       ├── adapters/
│       │   ├── clock.py        # SystemClock, FixedClock
│       │   ├── market_data.py  # StaticMarketDataAdapter
│       │   ├── options_chain.py# StaticOptionsChainAdapter
│       │   ├── presenters.py   # ConsolePresenter, JsonPresenter
│       │   ├── csv_logger.py   # CsvRecommendationLogger
│       │   ├── alert.py        # ConsoleAlertService, LoggingAlertService
│       │   ├── yfinance_market_data.py  # YFinanceMarketDataAdapter (live data)
│       │   ├── yfinance_historical.py   # YFinanceHistoricalDataAdapter (backtest)
│       │   ├── static_historical.py     # StaticHistoricalDataAdapter (testing)
│       │   ├── synthetic_chain.py       # SyntheticOptionsChainAdapter (Black-Scholes)
│       │   └── api/
│       │       ├── app.py      # FastAPI application factory, routes
│       │       └── models.py   # Pydantic request/response models
│       ├── application/
│       │   ├── use_cases.py    # AnalyzeAndRecommendUseCase
│       │   └── backtest.py     # RunBacktestUseCase
│       └── cli/
│           └── commands.py     # Click CLI commands
├── tests/
│   ├── domain/                 # Domain model, policy, and service tests
│   ├── adapters/               # Adapter unit tests
│   ├── application/            # Use case tests with mocked dependencies
│   ├── cli/                    # CLI integration tests
│   └── integration/            # End-to-end tests with real static adapters
├── pyproject.toml
├── tasks.py                    # Invoke task definitions
└── README.md
```

---

## Requirements

| Tool | Minimum Version | Check |
|------|----------------|-------|
| [Python](https://www.python.org/downloads/) | 3.13 | `python3 --version` |
| [uv](https://github.com/astral-sh/uv) | 0.4 | `uv --version` |

---

## Installation

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing, restart your terminal or run `source ~/.bashrc` (or `source ~/.zshrc`) so the `uv` command is available.

### 2. Clone the repository

```bash
git clone https://github.com/ocrosby/strike-pilot.git
cd strike-pilot
```

### 3. Install dependencies

```bash
uv sync --all-extras --dev
```

This installs both runtime and development dependencies (pytest, ruff, etc.) into a virtual environment managed by `uv`.

### 4. Verify the installation

```bash
uv run strike-pilot analyze --help
```

You should see a list of available options. If so, you're ready to go.

---

## CLI Usage

### `analyze` — intraday bias and spread recommendation

```bash
# Run analysis with defaults (console output, next-Friday expiry)
uv run strike-pilot analyze

# JSON output — machine-readable for downstream processing
uv run strike-pilot analyze --format json

# Live market data via Yahoo Finance
uv run strike-pilot analyze --data-source live

# Custom risk parameters
uv run strike-pilot analyze \
  --symbol SPX \
  --max-loss 1000 \
  --min-credit 75 \
  --spread-width 15 \
  --min-confidence 0.65

# Strike selection strategies
uv run strike-pilot analyze --strategy delta          # default: 20-delta short strike
uv run strike-pilot analyze --strategy pop            # target probability of profit
uv run strike-pilot analyze --strategy risk-reward    # target R/R ratio

# Expiry categories (repeatable)
uv run strike-pilot analyze --expiry-type 0dte
uv run strike-pilot analyze --expiry-type weekly --expiry-type monthly

# Specify an explicit expiry date (overrides --expiry-type)
uv run strike-pilot analyze --expiry 2024-02-16

# Log recommendations to CSV
uv run strike-pilot analyze --log-csv recommendations.csv

# Print a console alert when a spread is recommended
uv run strike-pilot analyze --alert

# Show all available options
uv run strike-pilot analyze --help
```

### `backtest` — replay the strategy over historical data

```bash
# Run a backtest over a date range using static demo data
uv run strike-pilot backtest --start 2024-01-15 --end 2024-01-19

# Use live Yahoo Finance historical data
uv run strike-pilot backtest \
  --start 2024-01-01 \
  --end 2024-03-31 \
  --data-source live

# JSON output for downstream processing
uv run strike-pilot backtest \
  --start 2024-01-15 \
  --end 2024-01-19 \
  --format json

# Show all available options
uv run strike-pilot backtest --help
```

### `serve` — start the HTTP API server

```bash
# Start on default host/port (127.0.0.1:8000)
uv run strike-pilot serve

# Custom host and port
uv run strike-pilot serve --host 0.0.0.0 --port 9000

# Show all available options
uv run strike-pilot serve --help
```

### Example Console Output

```
==================================================
SPX INTRADAY BIAS ANALYSIS
==================================================
Direction  : BULLISH
Confidence : 68.1%
Rationale  : Bullish momentum: price change 0.57%, RSI 58.0
==================================================

RECOMMENDATION: SPREAD TRADE
  Type       : Bull Put
  Short Leg  : SELL 5090.0 PUT
  Long Leg   : BUY 5080.0 PUT
  Expiry     : 2024-01-19
  Net Credit : $95.00
  Max Loss   : $905.00
  R/R Ratio  : 9.53
  Rationale  : Bull put spread: sell 5090.0P / buy 5080.0P
```

### Example JSON Output

```json
{
  "bias": {
    "direction": "bullish",
    "confidence": 0.6814,
    "rationale": "Bullish momentum: price change 0.57%, RSI 58.0"
  }
}
{
  "recommendation": {
    "action": "trade",
    "spread_type": "bull_put",
    "short_leg": { "strike": 5090.0, "expiry": "2024-01-19", "option_type": "put", "action": "sell", "premium": 4.76 },
    "long_leg":  { "strike": 5080.0, "expiry": "2024-01-19", "option_type": "put", "action": "buy",  "premium": 3.81 },
    "net_credit": 95.0,
    "max_loss": 905.0,
    "risk_reward_ratio": 9.53,
    "rationale": "Bull put spread: sell 5090.0P / buy 5080.0P"
  }
}
```

---

## Development Workflow

### Testing

```bash
# Run all tests with verbose output
uv run pytest tests/ -v

# Run a specific test module
uv run pytest tests/domain/test_services.py -v

# Run with coverage
uv run pytest tests/ --cov=src/strike_pilot
```

### Linting

```bash
uv run ruff check src tests
```

### Formatting

```bash
uv run ruff format src tests
```

### Invoke Tasks

```bash
uv run invoke lint      # ruff check
uv run invoke format    # ruff format
uv run invoke test      # pytest
uv run invoke check     # lint + test (pre-commit gate)
```

### Docker

The `serve` command runs a long-lived FastAPI/uvicorn process — a natural fit for containerization. The `Dockerfile` builds a minimal image using the official `uv` layer so dependency installation is fast and cached. Only runtime dependencies are installed (`--no-dev`), keeping the image lean.

`docker-compose` is intentionally absent: Strike Pilot has no backing services (no database, no cache), so a single container managed with `docker run` is the right scope. Add `docker-compose.yml` when a persistence or caching service joins the stack.

```bash
# Build the image (tagged strike-pilot:latest by default)
uv run invoke docker-build

# Force a clean build (no layer cache)
uv run invoke docker-build --no-cache

# Build with a specific tag
uv run invoke docker-build --tag 0.2.0

# Run the API server on localhost:8000
uv run invoke docker-run

# Bind a different host port
uv run invoke docker-run --port 9000

# Remove the local image
uv run invoke docker-clean
```

You can also use Docker directly if you prefer:

```bash
docker build -t strike-pilot .
docker run --rm -p 8000:8000 strike-pilot
```

Once running, the API is available at `http://localhost:8000`:

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "SPX"}'
```

---

## CI

GitHub Actions runs the full lint and test suite on every push and pull request.

Pipeline steps:
1. Checkout code
2. Set up Python 3.13
3. Install `uv`
4. `uv sync --all-extras --dev`
5. `uv run ruff check src tests`
6. `uv run pytest tests/ -v`

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the full configuration.

---

## Extending Strike Pilot

The architecture is built for extension. Common scenarios:

### Add an alternative bias strategy

1. Implement a class with an `analyze(snapshot: MarketSnapshot) -> MarketBias` method.
2. Pass it to `AnalyzeAndRecommendUseCase` via dependency injection.
3. Optionally expose it as a `--strategy` choice in `cli/commands.py`.

### Add a new strike selection strategy

1. Implement `StrikeSelectionStrategy` from `ports/interfaces.py`.
2. Wire it in `cli/commands.py` alongside the existing `delta`, `pop`, and `risk-reward` choices.

### Add a new output format

1. Implement `OutputPresenter` protocol methods (`present_bias`, `present_recommendation`).
2. Add a new `--format` choice in `cli/commands.py`.

### Add a new alert channel

1. Implement `AlertService` from `ports/interfaces.py` with an `alert(bias, recommendation)` method.
2. Instantiate and inject it via the `--alert` flag in `cli/commands.py`.
   See `adapters/alert.py` for reference implementations (console and logging).

### Add a new market data source

1. Implement `MarketDataProvider` and/or `HistoricalDataProvider` from `ports/interfaces.py`.
2. Add a new `--data-source` choice in `cli/commands.py` and wire the new adapter.
   `YFinanceMarketDataAdapter` and `YFinanceHistoricalDataAdapter` are the reference live implementations.

### Extend the HTTP API

1. Add new Pydantic request/response models in `adapters/api/models.py`.
2. Add new routes in `adapters/api/app.py`, delegating to existing use cases via dependency injection.
3. Domain and application layers remain untouched.

---

## Roadmap

- [x] Live market data adapter (e.g. yfinance, Tradier, IBKR)
- [x] IV rank / IV percentile signal integration
- [x] Multi-expiry recommendation support (0DTE vs weekly vs monthly)
- [x] Backtesting harness using historical data
- [x] Persistence adapter for logging recommendations to CSV/SQLite
- [x] Web API adapter (FastAPI) as an alternative inbound port
- [x] Advanced strike selection strategies (risk-reward targeting, probability of profit)
- [x] Alerting adapter (email, Slack, SMS)

