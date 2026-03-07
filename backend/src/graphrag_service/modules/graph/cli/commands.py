"""
Graph CLI commands for schema creation and data ingestion.
"""

import typer

from graphrag_service.cli.base import console, print_error, print_info, print_success
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
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
    def ingest():
        """Ingest entities and relationships into Neo4j."""
        print_info("Starting data ingestion...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)

            print_info("Ingesting nodes with embeddings...")
            usecase.ingest_nodes()

            print_info("Ingesting relationships...")
            usecase.ingest_relationships()

            print_success("Ingestion complete")
        except Exception as e:
            print_error(f"Ingestion failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

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
