# Strike Pilot

**SPX intraday bias and credit spread recommendation engine**

Strike Pilot analyzes intraday market signals for SPX and recommends credit spread trades (bull put or bear call) based on directional bias and configurable risk parameters.

## Architecture

Strike Pilot follows the **Ports and Adapters (Hexagonal)** architecture pattern:

```
src/strike_pilot/
├── domain/         # Pure business logic: models, policies, services
├── ports/          # Protocol interfaces (contracts for adapters)
├── adapters/       # Concrete implementations (clock, market data, options chain, presenters)
├── application/    # Use cases / orchestration
└── cli/            # Thin Click command wrappers
```

### Layer responsibilities

| Layer | Responsibility |
|-------|---------------|
| `domain` | Pure Python models and business rules — no I/O |
| `ports` | `Protocol`-based interfaces that decouple layers |
| `adapters` | Concrete implementations of ports (static/mock data today, live feeds tomorrow) |
| `application` | Orchestrates domain + adapters to execute use cases |
| `cli` | Wires dependencies and delegates to use cases |

## Requirements

- Python ≥ 3.11
- [uv](https://github.com/astral-sh/uv) (package manager)

## Installation

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the project and dev dependencies
uv sync --all-extras --dev
```

## Usage

### CLI

```bash
# Default analysis (console output)
uv run strike-pilot analyze

# JSON output
uv run strike-pilot analyze --format json

# Custom risk parameters
uv run strike-pilot analyze \
  --symbol SPX \
  --max-loss 1000 \
  --min-credit 75 \
  --spread-width 15 \
  --min-confidence 0.65

# Explicit expiry date
uv run strike-pilot analyze --expiry 2024-02-16

# Help
uv run strike-pilot --help
uv run strike-pilot analyze --help
```

### Example output

```
==================================================
SPX INTRADAY BIAS ANALYSIS
==================================================
Direction  : BULLISH
Confidence : 62.3%
Rationale  : Bullish momentum: price change 0.57%, RSI 58.0
==================================================

RECOMMENDATION: SPREAD TRADE
  Type       : Bull Put
  Short Leg  : SELL 5215.0 PUT
  Long Leg   : BUY 5205.0 PUT
  Expiry     : 2024-01-19
  Net Credit : $120.00
  Max Loss   : $880.00
  R/R Ratio  : 7.33
  Rationale  : Bull put spread: sell 5215.0P / buy 5205.0P
```

## Development

### Run tests

```bash
uv run pytest tests/ -v
```

### Run linter

```bash
uv run ruff check src tests
```

### Format code

```bash
uv run ruff format src tests
```

### Invoke tasks

```bash
uv run invoke lint      # lint only
uv run invoke test      # test only
uv run invoke check     # lint + test
uv run invoke format    # format code
```

## CI

GitHub Actions runs lint and tests on every push and pull request. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Extending

To add a live data source:

1. Create a new adapter in `src/strike_pilot/adapters/` that implements `MarketDataProvider` or `OptionsChainProvider` from `ports/interfaces.py`.
2. Wire it in `cli/commands.py` (or pass it in from a DI container).

The domain and application layers remain unchanged — only the adapter changes.
Predicts intraday SPX bias with confidence and converts market signals into structured credit spread ideas. Combines price action, volatility, and risk constraints to recommend strike selection or no-trade decisions.
