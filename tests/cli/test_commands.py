"""Unit tests for CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from strike_pilot.cli.commands import cli


class TestAnalyzeCommand:
    def test_analyze_runs_successfully(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze"])
        assert result.exit_code == 0

    def test_analyze_with_json_format(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--format", "json"])
        assert result.exit_code == 0
        assert "bias" in result.output or "recommendation" in result.output

    def test_analyze_with_custom_symbol(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--symbol", "SPX"])
        assert result.exit_code == 0

    def test_analyze_with_custom_risk_params(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["analyze", "--max-loss", "1000", "--min-credit", "100", "--spread-width", "15"],
        )
        assert result.exit_code == 0

    def test_analyze_with_explicit_expiry(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--expiry", "2024-02-16"])
        assert result.exit_code == 0

    def test_help_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Strike Pilot" in result.output

    def test_analyze_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "symbol" in result.output.lower()
