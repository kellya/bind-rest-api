""" test the cli functionality """
from click.testing import CliRunner
from bind_rest_api.cli import main as cli_main
from bind_rest_api.api.constants import __version__ as cli_version

runner = CliRunner()


def test_main():
    """validate main runs with successful exit"""
    response = runner.invoke(cli_main)
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
