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
- Applies a delta-targeting strategy to select spread strikes.
- Validates every candidate trade against configurable risk parameters before recommending it.
- Presents results in human-readable or machine-readable (JSON) format.

The architecture is deliberately designed for **replaceability**: swap in live market data, alternative bias strategies, or different output formats without touching the core domain logic.

---

## Architecture

Strike Pilot follows a pragmatic **Ports and Adapters (Hexagonal)** architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI (inbound adapter)                                          │
│  click commands — wires deps, delegates to use cases            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Application Layer                                              │
│  AnalyzeAndRecommendUseCase — orchestrates the full workflow    │
└──────┬───────────────────────────────────────────────────┬──────┘
       │ depends on ports (Protocols)                      │
┌──────▼──────────┐                          ┌─────────────▼──────┐
│  Domain Layer   │                          │  Adapters Layer    │
│  models         │                          │  StaticMarketData  │
│  policies       │                          │  StaticOptionsChain│
│  services       │                          │  ConsolePresenter  │
│  BiasStrategy   │                          │  JsonPresenter     │
│  StrikeSelector │                          │  SystemClock       │
└─────────────────┘                          └────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| `domain` | Pure Python models and business rules — zero I/O dependencies |
| `ports` | `Protocol`-based interfaces — contracts between layers |
| `adapters` | Concrete implementations (mock data today, live feeds tomorrow) |
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
│       │   └── services.py     # BiasStrategy, StrikeSelectionStrategy, implementations
│       ├── ports/
│       │   └── interfaces.py   # Protocol interfaces for all boundaries
│       ├── adapters/
│       │   ├── clock.py        # SystemClock, FixedClock
│       │   ├── market_data.py  # StaticMarketDataAdapter
│       │   ├── options_chain.py# StaticOptionsChainAdapter
│       │   └── presenters.py   # ConsolePresenter, JsonPresenter
│       ├── application/
│       │   └── use_cases.py    # AnalyzeAndRecommendUseCase
│       └── cli/
│           └── commands.py     # Click CLI commands
├── tests/
│   ├── domain/                 # Domain model, policy, and service tests
│   ├── adapters/               # Adapter unit tests
│   ├── application/            # Use case tests with mocked dependencies
│   └── cli/                    # CLI integration tests
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

```bash
# Run analysis with defaults (console output, next-Friday expiry)
uv run strike-pilot analyze

# JSON output — machine-readable for downstream processing
uv run strike-pilot analyze --format json

# Custom risk parameters
uv run strike-pilot analyze \
  --symbol SPX \
  --max-loss 1000 \
  --min-credit 75 \
  --spread-width 15 \
  --min-confidence 0.65

# Specify an explicit expiry date
uv run strike-pilot analyze --expiry 2024-02-16

# Show all available options
uv run strike-pilot analyze --help
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

### Add a live market data provider

1. Create `src/strike_pilot/adapters/live_market_data.py` implementing `MarketDataProvider` from `ports/interfaces.py`.
2. Wire it in `cli/commands.py`.
3. Domain and application layers remain untouched.

### Add an alternative bias strategy

1. Implement a class with an `analyze(snapshot: MarketSnapshot) -> MarketBias` method.
2. Pass it to `AnalyzeAndRecommendUseCase` via dependency injection.

### Add a new output format

1. Implement `OutputPresenter` protocol methods (`present_bias`, `present_recommendation`).
2. Add a new `--format` choice in `cli/commands.py`.

---

## Roadmap

- [ ] Live market data adapter (e.g. yfinance, Tradier, IBKR)
- [x] IV rank / IV percentile signal integration
- [x] Multi-expiry recommendation support (0DTE vs weekly vs monthly)
- [ ] Backtesting harness using historical data
- [x] Persistence adapter for logging recommendations to CSV/SQLite
- [ ] Web API adapter (FastAPI) as an alternative inbound port
- [ ] Advanced strike selection strategies (risk-reward targeting, probability of profit)
- [ ] Alerting adapter (email, Slack, SMS)

