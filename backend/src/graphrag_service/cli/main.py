"""
Main CLI entry point using Typer.
"""

import typer

from graphrag_service.cli.base import console
from graphrag_service.core.config import get_settings

app = typer.Typer(
    name="graphrag-service",
    help="GraphRAG Service CLI - Command-line interface for GraphRAG Service",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="none",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command()
def version():
    """Show application version."""
    settings = get_settings()
    console.print(f"[bold green]GraphRAG Service[/bold green] v{settings.APP_VERSION}")


# Register module commands
try:
    from graphrag_service.modules.graph.cli.commands import get_graph_app

    app.add_typer(get_graph_app(), name="graph")
except ImportError:
    pass

try:
    from graphrag_service.modules.health.cli.commands import get_health_app

    app.add_typer(get_health_app(), name="health")
except ImportError:
    pass


def main():
    """Main CLI entry point."""
    import sys

    if "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) == 1:
        try:
            app()
        except (TypeError, AttributeError) as e:
            if "make_metavar" in str(e) or "ctx" in str(e):
                import click

                click.echo("GraphRAG Service CLI")
                click.echo("\nAvailable commands:")
                click.echo("  version              Show application version")
                click.echo("  graph                Graph database management")
                click.echo("    schema             Create Neo4j schema")
                click.echo("    ingest             Ingest data into Neo4j")
                click.echo("    status             Show graph database status")
                click.echo("  health               Health check commands")
                click.echo("    ping               Simple liveness check")
                click.echo("    check              Check Neo4j connectivity")
                click.echo("\nUse 'cli <command> --help' for more information")
                sys.exit(0)
            raise
    else:
        app()


if __name__ == "__main__":
    main()
