"""Evaluation CLI commands."""

import json
import sys
from pathlib import Path

import typer

from graphrag_service.cli.base import console, print_error, print_info, print_success


def get_eval_app() -> typer.Typer:
    """Create evaluation CLI sub-app."""
    app = typer.Typer(
        name="eval",
        help="Evaluation framework commands",
        no_args_is_help=True,
    )

    @app.command()
    def run(
        category: str = typer.Option("", help="Run only this category (e.g. FACTUAL_LOOKUP)"),
        output: str = typer.Option("", help="Output JSON file path"),
        markdown: bool = typer.Option(False, help="Also output markdown report"),
    ):
        """Run evaluation suite against the RAG pipeline."""
        # Import here to avoid circular imports and loading models at CLI parse time
        from tests.evaluation.queries import get_all_queries, get_queries_by_category
        from tests.evaluation.runner import EvaluationRunner

        from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
        from graphrag_service.modules.rag.usecase import RAGUseCase

        try:
            client = get_neo4j_client()
            usecase = RAGUseCase(client)

            if category:
                queries = get_queries_by_category(category.upper())
                if not queries:
                    print_error(f"No queries found for category: {category}")
                    raise typer.Exit(code=1)
                print_info(f"Running {len(queries)} queries for category: {category}")
            else:
                queries = get_all_queries()
                print_info(f"Running {len(queries)} evaluation queries...")

            runner = EvaluationRunner(
                pipeline_fn=usecase.query,
                queries=queries,
            )
            report = runner.run_all(system_name="graphrag")

            # Console output
            console.print(report.to_console())

            # Save JSON
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_text(report.to_json())
                print_success(f"Report saved to {output}")

            # Save markdown
            if markdown:
                md_path = output.replace(".json", ".md") if output else "results/eval_report.md"
                Path(md_path).parent.mkdir(parents=True, exist_ok=True)
                Path(md_path).write_text(report.to_markdown())
                print_success(f"Markdown report saved to {md_path}")

        except Exception as e:
            print_error(f"Evaluation failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    @app.command()
    def queries(
        category: str = typer.Option("", help="Filter by category"),
    ):
        """List all evaluation queries."""
        from tests.evaluation.queries import CATEGORIES, get_all_queries, get_queries_by_category

        if category:
            qs = get_queries_by_category(category.upper())
        else:
            qs = get_all_queries()

        for q in qs:
            console.print(
                f"  [{q.difficulty}] {q.id}: {q.question}"
            )
        console.print(f"\nTotal: {len(qs)} queries")

    return app
