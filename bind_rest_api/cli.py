""" cli entry point for setting up the fastapi app with options passed"""
import click
import uvicorn
from bind_rest_api.api.constants import VERSION


@click.command()
@click.option(
    "--host", "-H", default="127.0.0.1", help="host/IP to bind to for the api service"
)
@click.option(
    "--port", "-P", default=8000, help="TCP port to bind to for the api service"
)
@click.option("--workers", "-w", default=3, help="Number of workers to deploy")
@click.option("--dry-run", "-n", is_flag=True, help="Do not actually run - for testing")
@click.version_option(version=VERSION)
def main(host, port, workers, dry_run):
    """main logic for the cli"""
    if not dry_run:  # pragma: no cover
        uvicorn.run(
            "bind_rest_api.api.api:app",
            host=host,
            port=port,
            reload=True,
            debug=True,
            workers=workers,
        )
    else:
        print("would run with the following options:")
        print(f"host: {host}")
        print(f"port: {port}")
        print(f"workers: {workers}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter #pragma: no cover
