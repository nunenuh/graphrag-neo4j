"""
Health CLI commands.
"""

import typer

from graphrag_service.cli.base import print_error, print_success
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client


def get_health_app() -> typer.Typer:
    """Create health CLI sub-app."""
    app = typer.Typer(
        name="health",
        help="Health check commands",
        no_args_is_help=True,
    )

    @app.command()
    def ping():
        """Simple liveness check."""
        print_success("pong")

    @app.command()
    def check():
        """Check Neo4j connectivity."""
        try:
            client = get_neo4j_client()
            if client.verify_connection():
                print_success("Neo4j: connected")
            else:
                print_error("Neo4j: unreachable")
        except Exception as e:
            print_error(f"Health check failed: {e}")
        finally:
            close_neo4j_client()

    return app
