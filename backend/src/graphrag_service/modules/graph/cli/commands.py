"""
Graph CLI commands for schema creation and data ingestion.
"""

from typing import Optional

import typer

from graphrag_service.cli.base import console, print_error, print_info, print_success, print_warning
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
from graphrag_service.modules.graph.checkpoint import (
    format_checkpoint_report,
    load_checkpoint,
    reset_checkpoint,
)
from graphrag_service.modules.graph.usecase import GraphUseCase


def get_graph_app() -> typer.Typer:
    """Create graph CLI sub-app."""
    app = typer.Typer(
        name="graph",
        help="Graph database management commands",
        no_args_is_help=True,
    )

    @app.command()
    def schema():
        """Create Neo4j constraints and vector indexes."""
        print_info("Creating Neo4j schema...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)
            usecase.create_schema()
            print_success("Schema created successfully")
        except Exception as e:
            print_error(f"Schema creation failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command()
    def ingest(
        node_type: Optional[str] = typer.Option(
            None, "--type", "-t",
            help="Only ingest this node type (Paper, Method, Task, Dataset).",
        ),
        offset: int = typer.Option(
            0, "--offset", "-o",
            help="Skip this many valid items before processing.",
        ),
        limit: int = typer.Option(
            0, "--limit", "-l",
            help="Process at most this many items (0 = unlimited).",
        ),
        resume: bool = typer.Option(
            False, "--resume", "-r",
            help="Resume from last checkpoint, skipping completed node types.",
        ),
        skip_embedded: bool = typer.Option(
            False, "--skip-embedded",
            help="Skip embedding for nodes that already have vectors in Neo4j.",
        ),
        reset: bool = typer.Option(
            False, "--reset",
            help="Reset progress checkpoint before starting.",
        ),
        no_relationships: bool = typer.Option(
            False, "--no-relationships",
            help="Skip relationship ingestion (nodes only).",
        ),
    ):
        """Ingest entities and relationships into Neo4j.

        Supports resuming, offset/limit batching, and skipping already-embedded nodes.
        """
        if reset:
            reset_checkpoint()
            print_info("Progress checkpoint reset")

        print_info("Starting data ingestion...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)

            print_info("Ingesting nodes with embeddings...")
            usecase.ingest_nodes(
                node_type=node_type,
                offset=offset,
                limit=limit,
                resume=resume,
                skip_embedded=skip_embedded,
            )

            if not no_relationships:
                print_info("Ingesting relationships...")
                usecase.ingest_relationships()

            print_success("Ingestion complete")
        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(code=1)
        except Exception as e:
            print_error(f"Ingestion failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command(name="ingest-status")
    def ingest_status():
        """Show ingestion progress from checkpoint file."""
        checkpoint = load_checkpoint()
        if not checkpoint.node_types:
            print_warning("No ingestion progress recorded yet.")
            raise typer.Exit()
        report = format_checkpoint_report(checkpoint)
        console.print(report)

    @app.command()
    def status():
        """Show graph database status."""
        try:
            client = get_neo4j_client()
            connected = client.verify_connection()
            if connected:
                print_success("Neo4j is connected")
                usecase = GraphUseCase(client)
                labels, rels = usecase.get_schema()
                console.print(f"  Node labels: {labels}")
                console.print(f"  Relationship types: {rels}")
            else:
                print_error("Neo4j is not reachable")
        except Exception as e:
            print_error(f"Status check failed: {e}")
        finally:
            close_neo4j_client()

    return app
