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

    def test_analyze_invalid_format(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--format", "xml"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid choice" in result.output.lower()

    def test_analyze_negative_max_loss(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--max-loss", "-500"])
        assert result.exit_code != 0

    def test_analyze_negative_min_credit(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--min-credit", "-10"])
        assert result.exit_code != 0

    def test_analyze_confidence_above_one(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--min-confidence", "1.5"])
        assert result.exit_code != 0

    def test_analyze_confidence_below_zero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--min-confidence", "-0.1"])
        assert result.exit_code != 0

    def test_analyze_negative_spread_width(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--spread-width", "-5"])
        assert result.exit_code != 0

    def test_analyze_with_expiry_type_weekly(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--expiry-type", "weekly"])
        assert result.exit_code == 0

    def test_analyze_with_multiple_expiry_types(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["analyze", "--expiry-type", "0dte", "--expiry-type", "monthly"]
        )
        assert result.exit_code == 0

    def test_analyze_expiry_overrides_expiry_type(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["analyze", "--expiry", "2024-02-16", "--expiry-type", "monthly"],
        )
        assert result.exit_code == 0

    def test_analyze_default_uses_multi(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze"])
        assert result.exit_code == 0

    def test_analyze_invalid_expiry_type(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--expiry-type", "biweekly"])
        assert result.exit_code != 0
