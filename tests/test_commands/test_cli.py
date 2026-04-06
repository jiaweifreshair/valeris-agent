"""CLI smoke tests."""

from typer.testing import CliRunner

from openharness.cli import app


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Velaris" in result.output
