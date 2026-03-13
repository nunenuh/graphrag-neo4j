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
            None, "--type",
            help="Only ingest this node type (Paper, Method, Task, Dataset).",
        ),
        offset: int = typer.Option(
            0, "--offset",
            help="Skip this many valid items before processing.",
        ),
        limit: int = typer.Option(
            0, "--limit",
            help="Process at most this many items (0 = unlimited).",
        ),
        resume: bool = typer.Option(
            False,
            help="Resume from last checkpoint, skipping completed node types.",
        ),
        skip_embedded: bool = typer.Option(
            False,
            help="Skip embedding for nodes that already have vectors in Neo4j.",
        ),
        reset: bool = typer.Option(
            False,
            help="Reset progress checkpoint before starting.",
        ),
        skip_relationships: bool = typer.Option(
            False,
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

            if not skip_relationships:
                print_info("Ingesting relationships...")
                usecase.ingest_relationships()

            print_info("Ingesting authors with entity resolution...")
            usecase.ingest_authors()

            print_success("Ingestion complete")
        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(code=1)
        except Exception as e:
            print_error(f"Ingestion failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command(name="ingest-rels")
    def ingest_rels():
        """Ingest relationships only (AUTHORED, USED_FOR, EVALUATED_ON)."""
        print_info("Ingesting relationships...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)
            usecase.ingest_relationships()
            print_success("Relationship ingestion complete")
        except Exception as e:
            print_error(f"Relationship ingestion failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command(name="ingest-authors")
    def ingest_authors(
        batch_size: int = typer.Option(500, help="Batch size for Neo4j operations"),
    ) -> None:
        """Run author extraction + entity resolution + relationship creation."""
        print_info("Ingesting authors with entity resolution...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)
            result = usecase.ingest_authors(batch_size=batch_size)
            print_success(
                f"Authors: {result['raw_authors']} raw -> {result['canonical_authors']} canonical\n"
                f"Edges: {result['authored_edges']} AUTHORED, {result['coauthor_edges']} CO_AUTHORED_WITH"
            )
        except Exception as e:
            print_error(f"Author ingestion failed: {e}")
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
    def verify():
        """Run comprehensive graph integrity checks."""
        print_info("Running graph verification checks...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)
            results = usecase.verify_graph()

            # Node counts
            console.print("\n[bold]Node Counts[/bold]")
            for label, count in results["node_counts"].items():
                console.print(f"  {label}: {count:,}")

            # Edge counts
            console.print("\n[bold]Relationship Counts[/bold]")
            for rel_type, count in results["edge_counts"].items():
                console.print(f"  {rel_type}: {count:,}")

            # Orphan nodes
            console.print("\n[bold]Orphan Nodes (no relationships)[/bold]")
            for label, count in results["orphan_counts"].items():
                if count > 0:
                    print_warning(f"  {label}: {count:,} orphans")
                else:
                    console.print(f"  {label}: 0")

            # Missing embeddings
            console.print("\n[bold]Missing Embeddings[/bold]")
            for label, count in results["missing_embeddings"].items():
                if count > 0:
                    print_warning(f"  {label}: {count:,} missing")
                else:
                    console.print(f"  {label}: 0")

            # Duplicates
            if results["duplicates"]:
                console.print("\n[bold]Duplicate Names[/bold]")
                for label, dupes in results["duplicates"].items():
                    for d in dupes:
                        print_warning(f"  {label}: \"{d['name']}\" x{d['count']}")
            else:
                console.print("\n[bold]Duplicate Names:[/bold] None")

            # Vector indexes
            console.print(f"\n[bold]Vector Indexes:[/bold] {len(results.get('vector_indexes', []))} found")
            for idx in results.get("vector_indexes", []):
                console.print(f"  {idx['name']} → {idx['labelsOrTypes']}")

            # Constraints
            console.print(f"[bold]Constraints:[/bold] {results.get('constraints_count', 0)}")

            # Summary
            console.print("\n[bold]Checks Summary[/bold]")
            for check in results["checks"]:
                icon = "✓" if check["passed"] else "✗"
                style = "green" if check["passed"] else "red"
                console.print(f"  [{style}]{icon}[/{style}] {check['name']}: {check['detail']}")

            if results["passed"]:
                print_success("\nAll checks passed!")
            else:
                print_error("\nSome checks failed — review above.")
                raise typer.Exit(code=1)

        except typer.Exit:
            raise
        except Exception as e:
            print_error(f"Verification failed: {e}")
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
                stats = usecase.get_stats()
                console.print("  Node counts:")
                for label, count in stats.get("node_counts", {}).items():
                    console.print(f"    {label}: {count:,}")
                console.print(f"  Total relationships: {stats.get('relationship_count', 0):,}")
            else:
                print_error("Neo4j is not reachable")
        except Exception as e:
            print_error(f"Status check failed: {e}")
        finally:
            close_neo4j_client()

    return app
