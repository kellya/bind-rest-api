""" test the cli functionality """
from click.testing import CliRunner
from bind_rest_api.cli import main as cli_main
from bind_rest_api.api.constants import __version__ as cli_version

runner = CliRunner()


def test_main():
    """validate main runs with successful exit"""
    response = runner.invoke(cli_main, ["--dry-run"])
    assert response.exit_code == 0


def test_version():
    """verify version responds with the current version number"""
    response = runner.invoke(cli_main, ["--version"])
    assert response.exit_code == 0
    assert cli_version in response.output


def test_help():
    """verify --help outputs help information"""
    response = runner.invoke(cli_main, ["--help"])
    assert response.exit_code == 0


def test_host():
    """verify host specified is applied to command"""
    response = runner.invoke(cli_main, ["--dry-run", "--host", "1.2.3.4"])
    assert response.exit_code == 0
    assert "1.2.3.4" in response.output


def test_port():
    """verify port specified is applied to command"""
    response = runner.invoke(cli_main, ["--dry-run", "--port", "9999"])
    assert response.exit_code == 0
    assert "9999" in response.output
