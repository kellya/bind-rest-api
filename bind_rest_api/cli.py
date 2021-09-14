""" cli entry point for setting up the fastapi app with options passed"""
import click
import uvicorn
from bind_rest_api.api.constants import VERSION
from .password import generate_password


@click.group(name="bindapi", invoke_without_command=True)
@click.pass_context
@click.option(
    "--host", "-H", default="127.0.0.1", help="host/IP to bind to for the api service"
)
@click.option(
    "--port", "-P", default=8000, help="TCP port to bind to for the api service"
)
@click.option("--workers", "-w", default=3, help="Number of workers to deploy")
@click.option("--dry-run", "-n", is_flag=True, help="Do not actually run - for testing")
@click.version_option(version=VERSION)
def main(ctx, host, port, workers, dry_run):
    """main logic for the cli"""
    if not dry_run and not ctx.invoked_subcommand:  # pragma: no cover
        uvicorn.run(
            "bind_rest_api.api.api:app",
            host=host,
            port=port,
            reload=True,
            debug=True,
            workers=workers,
        )
    elif dry_run and not ctx.invoked_subcommand:
        print("would run with the following options:")
        print(f"host: {host}")
        print(f"port: {port}")
        print(f"workers: {workers}")


@main.command()
@click.option("--username", "-u", default=None, help="Generate a username")
@click.option(
    "--length", "-l", default=64, help="Specify length of password to generate"
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
