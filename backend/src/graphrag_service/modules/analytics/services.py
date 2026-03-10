"""Analytics service — orchestrates library calls for graph analytics.

Does NOT access the database. Uses library/ for computation.
"""

import json
from pathlib import Path

from loguru import logger

from graphrag_service.core.config import get_settings
from graphrag_service.library.analytics.centrality import (
    compute_centrality,
    compute_h_index_from_edges,
)
from graphrag_service.library.analytics.community import (
    build_coauthorship_graph,
    detect_communities,
)
from graphrag_service.library.analytics.trends import (
    build_entity_year_counts,
    compute_diffusion_paths,
    compute_trend_scores,
)
from graphrag_service.library.parsers import load_json


class AnalyticsService:
    """Service for graph analytics. Does NOT access the database."""

    @staticmethod
    def data_dir() -> Path:
        settings = get_settings()
        path = Path(settings.DATA_DIR)
        if path.is_absolute():
            return path
        return Path(__file__).parent.parent.parent.parent.parent.parent / settings.DATA_DIR

    def run_community_detection(
        self, authored_edges: list[dict]
    ) -> dict[str, int]:
        """Build co-authorship graph and detect communities."""
        graph = build_coauthorship_graph(authored_edges)
        logger.info(
            f"Co-authorship graph: {graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )
        communities = detect_communities(graph)
        logger.info(f"Detected {len(set(communities.values()))} communities")
        return communities

    def run_centrality(
        self, authored_edges: list[dict]
    ) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
        """Compute centrality metrics and h-index."""
        graph = build_coauthorship_graph(authored_edges)
        centrality = compute_centrality(graph)
        h_indices = compute_h_index_from_edges(authored_edges)
        logger.info(f"Computed centrality for {len(centrality)} authors")
        return centrality, h_indices

    def run_trend_scoring(self) -> tuple[dict[str, float], dict[str, float], dict[str, str]]:
        """Compute trend scores for methods and tasks."""
        eval_path = self.data_dir() / "evaluations.json"
        evaluations = load_json(eval_path)

        method_counts = build_entity_year_counts(evaluations, entity_type="method")
        task_counts = build_entity_year_counts(evaluations, entity_type="task")

        method_trends = compute_trend_scores(method_counts)
        task_trends = compute_trend_scores(task_counts)

        # Build diffusion paths (method → tasks over time)
        method_task_data: dict[str, list[dict]] = {}
        for ev in evaluations:
            task_name = ev.get("task", "")
            if not task_name:
                continue
            for ds_entry in ev.get("datasets", []):
                for row in ds_entry.get("sota", {}).get("rows", []):
                    method_name = row.get("model_name", "")
                    if not method_name:
                        continue
                    date_str = str(row.get("paper_date", "unknown"))
                    year = date_str[:4] if date_str != "unknown" else "unknown"
                    if method_name not in method_task_data:
                        method_task_data[method_name] = []
                    method_task_data[method_name].append(
                        {"task": task_name, "year": year, "paper_count": 1}
                    )

        diffusion = compute_diffusion_paths(method_task_data)
        logger.info(
            f"Computed trends: {len(method_trends)} methods, {len(task_trends)} tasks"
        )
        return method_trends, task_trends, diffusion
