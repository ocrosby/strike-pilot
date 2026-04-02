# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Test coverage reporting in CI with 90% minimum threshold
- `py.typed` marker for PEP 561 typed package support
- `mypy` strict type checking in CI
- `ruff format --check` enforcement in CI
- `.pre-commit-config.yaml` with ruff lint and format hooks
- Dependabot configuration for GitHub Actions and pip dependency updates
- Integration/smoke test using real static adapters (no mocks)
- Expanded CLI tests covering invalid input edge cases
- `CLAUDE.md` for Claude Code integration

### Changed
- Upgraded Python version from 3.11 to 3.13
- Upgraded GitHub Actions to Node.js 24-compatible versions
- Pinned `uv` version in CI for reproducibility
- Improved README installation instructions with numbered steps and verification
- Moved `invoke` from runtime to dev-only dependency

## [0.1.0] - 2025-01-01

### Added
- Initial release of Strike Pilot
- SPX intraday bias analysis via `SimpleMomentumBiasStrategy`
- Delta-based credit spread strike selection
- Risk parameter validation policies
- Static market data and options chain adapters
- Console and JSON output presenters
- Click CLI with `analyze` command
- Hexagonal architecture with ports and adapters
- Full test suite across all layers
- GitHub Actions CI pipeline with lint and test
