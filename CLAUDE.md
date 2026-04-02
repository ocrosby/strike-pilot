# CLAUDE.md

This file provides context for Claude Code when working in this repository.

## Project overview

Strike Pilot is a Python-based SPX intraday bias and credit spread recommendation engine. It aggregates momentum signals to determine directional bias (bullish/bearish/neutral) and recommends credit spreads validated against configurable risk parameters.

## Architecture

Hexagonal (Ports & Adapters) architecture with strict layer separation:

- **domain/** — Pure business logic: models (frozen dataclasses), policies (pure validation functions), services (strategy implementations). Zero I/O dependencies.
- **ports/** — Protocol-based interfaces defining contracts between layers. All protocols are `@runtime_checkable`.
- **adapters/** — Concrete implementations: static market data, options chains, console/JSON presenters, clocks.
- **application/** — Use case orchestration. Composes domain services with adapters via dependency injection.
- **cli/** — Thin Click CLI layer. Wires dependencies and delegates to use cases. No business logic here.

**Key principle**: Domain and application layers depend only on protocols from `ports/`, never on concrete adapters. New data sources or output formats are added by implementing the relevant protocol and wiring it in `cli/commands.py`.

## Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ -v --cov=src/strike_pilot --cov-report=term-missing --cov-fail-under=90

# Lint
uv run ruff check src tests

# Format
uv run ruff format src tests

# Type check
uv run mypy src

# Run the CLI
uv run strike-pilot analyze
uv run strike-pilot analyze --format json

# Invoke tasks (convenience wrappers)
uv run invoke lint
uv run invoke format
uv run invoke test
uv run invoke check    # lint + test
```

## Code conventions

- **Python 3.13+** — enforced via `.python-version`, `pyproject.toml`, and CI
- **Frozen dataclasses** for all domain value types
- **Protocols** (not ABC) for all port interfaces
- **Double quotes** for strings (enforced by ruff)
- **Line length**: 100 characters
- **Type annotations** on all public functions — enforced by mypy strict mode
- **Ruff lint rules**: E, F, I, N, UP, ANN, B, C4, SIM, RUF
- **No business logic in CLI or adapters** — those are thin wiring/formatting layers

## Testing conventions

- Tests mirror source structure: `tests/domain/`, `tests/adapters/`, `tests/application/`, `tests/cli/`, `tests/integration/`
- Unit tests use mocks for cross-layer dependencies
- Integration tests in `tests/integration/` use real static adapters (no mocks) to verify wiring
- Test classes are named `Test<ClassName>`, test methods `test_<behavior>`
- Use `from __future__ import annotations` in all files
- Minimum 90% test coverage enforced in CI

## CI pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and PR:
1. Ruff lint check
2. Ruff format check
3. Mypy strict type check
4. Pytest with coverage (90% minimum)

## When making changes

- Run `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run pytest tests/ -v --cov=src/strike_pilot --cov-fail-under=90` before committing
- New domain types should be frozen dataclasses
- New adapters must implement the relevant Protocol from `ports/interfaces.py`
- New features need tests in the appropriate `tests/` subdirectory
- Keep the CLI layer thin — push logic into domain services or application use cases
