"""Entity resolution CLI commands for author ingestion and deduplication."""

import typer

from graphrag_service.cli.base import console, print_error, print_info, print_success
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
from graphrag_service.modules.entity_resolution.usecase import ERUseCase


def get_er_app() -> typer.Typer:
    """Create entity resolution CLI sub-app."""
    app = typer.Typer(
        name="er",
        help="Entity resolution commands (author ingestion and deduplication)",
        no_args_is_help=True,
    )

    @app.command()
    def ingest():
        """Ingest Author nodes and AUTHORED relationships from PwC data."""
        print_info("Ingesting authors...")
        try:
            client = get_neo4j_client()
            usecase = ERUseCase(client)
            count = usecase.ingest_authors()
            print_success(f"Ingested {count} authors")
        except Exception as e:
            print_error(f"Author ingestion failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command()
    def resolve():
        """Run entity resolution on Author nodes (blocking + scoring + merge)."""
        print_info("Running entity resolution...")
        try:
            client = get_neo4j_client()
            usecase = ERUseCase(client)
            result = usecase.resolve()
            print_success(
                f"Resolution complete: {result['clusters_found']} clusters, "
                f"{result['authors_merged']} authors merged"
            )
        except Exception as e:
            print_error(f"Entity resolution failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command()
    def stats():
        """Show entity resolution statistics."""
        try:
            client = get_neo4j_client()
            usecase = ERUseCase(client)
            s = usecase.get_stats()
            console.print(f"  Total authors:    {s['total_authors']}")
            console.print(f"  Canonical:        {s['canonical_authors']}")
            console.print(f"  Merged:           {s['merged_authors']}")
            console.print(f"  AUTHORED rels:    {s['total_authored_rels']}")
        except Exception as e:
            print_error(f"Stats failed: {e}")
        finally:
            close_neo4j_client()

    return app
