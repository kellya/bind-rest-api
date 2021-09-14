""" test the cli functionality """
from click.testing import CliRunner
from bind_rest_api.cli import main as cli_main
from bind_rest_api.api.constants import __version__ as cli_version
import os
from unittest import mock


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


def test_bind_server():
    """verify that a specified --bind-server works"""
    bind_server = "192.168.0.1"
    response = runner.invoke(cli_main, ["--dry-run", "--bind-server", bind_server])
    assert response.exit_code == 0
    assert bind_server in response.output
    response = runner.invoke(cli_main, ["--dry-run", "--bind-server", ""])
    assert "bind server: 127.0.0.1" in response.output


@mock.patch.dict(os.environ, {"BIND_SERVER": "192.168.0.1"})
def test_env_values():
    """validate behavior with values from environment variables"""
    response = runner.invoke(
        cli_main,
        [
            "--dry-run",
        ],
    )
    assert response.exit_code == 0
    assert "bind server: 192.168.0.1" in response.output


def test_password():
    """Verify the password generation"""
    response = runner.invoke(cli_main, ["add-key"])
    # just generating a key should give a 64 char string
    assert len(response.output.strip()) == 64
    response = runner.invoke(cli_main, ["add-key", "-l", "96"])
    # if we specify a number, we should get that number of chars resturned
    assert len(response.output.strip()) == 96
    username = "testuser"
    response = runner.invoke(cli_main, ["add-key", "-u", username, "-l", "96"])
    # if we specify a username, it shoudl output that username comma and the
    # password.  So it should start with username,
    assert response.output.startswith(f"{username},")
    # We should get total chars of password_length + username_length + 1 for
    # the comma
    assert len(response.output.strip()) == 96 + len(username) + 1
    response1 = runner.invoke(cli_main, ["add-key"])
    response2 = runner.invoke(cli_main, ["add-key"])
    # subsequent calls should generate random data.  There should be no way
    # this is ever equal.
    assert response1.output.strip() != response2.output.strip()
