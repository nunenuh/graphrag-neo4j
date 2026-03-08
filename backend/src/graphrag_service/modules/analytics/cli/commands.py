"""Analytics CLI commands for graph analytics pipeline."""

import typer

from graphrag_service.cli.base import console, print_error, print_info, print_success
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
from graphrag_service.modules.analytics.usecase import AnalyticsUseCase


def get_analytics_app() -> typer.Typer:
    """Create analytics CLI sub-app."""
    app = typer.Typer(
        name="analytics",
        help="Graph analytics commands (community detection, centrality, trends)",
        no_args_is_help=True,
    )

    @app.command()
    def run():
        """Run the full analytics pipeline."""
        print_info("Running analytics pipeline...")
        try:
            client = get_neo4j_client()
            usecase = AnalyticsUseCase(client)
            result = usecase.run_all()
            print_success(
                f"Analytics complete: "
                f"{result['communities_detected']} communities, "
                f"{result['authors_with_centrality']} authors with centrality, "
                f"{result['methods_with_trends']} methods with trends"
            )
        except Exception as e:
            print_error(f"Analytics pipeline failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command()
    def communities():
        """Show detected communities."""
        try:
            client = get_neo4j_client()
            usecase = AnalyticsUseCase(client)
            rows = usecase.get_communities(limit=20)
            if not rows:
                print_info("No communities detected. Run 'analytics run' first.")
                return
            for r in rows:
                console.print(
                    f"  Community {r['cid']}: {r['member_count']} members"
                )
        except Exception as e:
            print_error(f"Failed: {e}")
        finally:
            close_neo4j_client()

    @app.command()
    def trends(
        entity_type: str = typer.Argument("Method", help="Method or Task"),
        limit: int = typer.Option(10, help="Number of results"),
    ):
        """Show top trending methods or tasks."""
        try:
            client = get_neo4j_client()
            usecase = AnalyticsUseCase(client)
            rows = usecase.get_trending(entity_type=entity_type, limit=limit)
            if not rows:
                print_info("No trend data. Run 'analytics run' first.")
                return
            for r in rows:
                console.print(
                    f"  {r['name']}: trend_score={r['trend_score']:.4f}"
                )
        except Exception as e:
            print_error(f"Failed: {e}")
        finally:
            close_neo4j_client()

    return app
