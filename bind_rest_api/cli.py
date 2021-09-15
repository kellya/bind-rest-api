""" cli entry point for setting up the fastapi app with options passed"""
import os
import sys
import click
import uvicorn
from bind_rest_api.api.constants import VERSION
from .password import generate_password


@click.group(name="bindapi", invoke_without_command=True)
@click.pass_context
@click.option(
    "--host",
    "-H",
    help="host/IP to bind to for the api service",
)
@click.option(
    "--port",
    "-P",
    default=8000,
    help="TCP port to bind to for the api service",
    show_default="8000",
)
@click.option("--workers", "-w", default=3, help="Number of workers to deploy")
@click.option("--dry-run", "-n", is_flag=True, help="Do not actually run - for testing")
@click.option("--debug", is_flag=True, help="Pass debug flag to uvicorn")
@click.option(
    "--bind-server",
    envvar="BIND_SERVER",
    help=(
        "The BIND server the api will use to make dynamic changes. "
        "Will read from environment variable BIND_SERVER"
    ),
    show_default="127.0.0.1",
)
@click.option(
    "--bind-user",
    envvar="TSIG_USERNAME",
    prompt=True,
    help=(
        "The user/TSIG keyname to connect to the bind server as. "
        "Will read from environment variable TSIG_USERNAME"
    ),
)
@click.option(
    "--bind-pass",
    envvar="TSIG_PASSWORD",
    prompt=True,
    help=(
        "The TSIG key secret to pass to the bind server."
        "  Will read from environment variable TSIG_PASSWORD"
        "\n\nWARNING: This value can be read in a process list output"
    ),
)
@click.option(
    "--api-key-file",
    default=lambda: os.environ.get("API_KEY_FILE", ""),
    help="The file that keeps keyname and secret for API access",
    show_default="apikeys.pass",
)
@click.version_option(version=VERSION)
def main(
    ctx,
    host,
    port,
    workers,
    dry_run,
    bind_server,
    bind_pass,
    bind_user,
    api_key_file,
    debug,
):
    """main logic for the cli"""
    # if we don't get a host from env, use localhost
    if not host:
        host = "127.0.0.1"
    # if no bind server was given, assume localhost
    if not bind_server:
        bind_server = "127.0.0.1"
    # if no api_key_file was given, assume apikeys.pass
    if not api_key_file:
        api_key_file = "apikeys.pass"  # pragma: no cover
        # The test_cli's test_api_key_file is explicitly testing this, I don't
        # know why coverage isn't seeing this, so I pragma: no covered the
        # api_key_file_check
        # I don't want to test the api running through the CLI, that will be
        # separate testing so skip coverage of this section also
    if not dry_run and not ctx.invoked_subcommand:  # pragma: no cover
        # We can't assume TSIG values, if they aren't in env or passed via
        # options just error out
        if not bind_pass or not bind_user:
            print(
                "Error BIND TSIG information was not given\n"
                " TSIG_USERNAME and TSGI_PASSWORD must be set in environment vars"
                " or you must specify --bind-user and --bind-password"
            )
            sys.exit(1)
        uvicorn.run(
            "bind_rest_api.api.api:app",
            host=host,
            port=port,
            reload=True,
            debug=debug,
            workers=workers,
        )
    elif dry_run and not ctx.invoked_subcommand:
        print("would run with the following options:")
        print()
        click.echo(click.style("              API", bold=True))
        print(f"         host: {host}")
        print(f"         port: {port}")
        print(f"      workers: {workers}")
        print(f" api key file: {api_key_file}")
        print()
        click.echo(click.style("          BIND Server", bold=True))
        print(f"  bind server: {bind_server}")
        print(f"         port: {port}")
        print(f"    TSIG user: {bind_user}")
        print(f"    TSIG pass: {bind_pass}")


@main.command()
@click.option("--username", "-u", default=None, help="Generate a username")
@click.option(
    "--length",
    "-l",
    default=64,
    help="Specify length of password to generate",
    show_default="64",
)
def add_key(username, length):
    """Create a key to add to the api keys"""
    password = generate_password(length)
    if username:
        print(f"{username},{password}")
    else:
        print(password)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter #pragma: no cover
