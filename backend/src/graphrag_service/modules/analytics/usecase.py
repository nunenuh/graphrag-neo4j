"""Analytics use case — coordinates service + repository."""

from loguru import logger

from graphrag_service.dbase.neo4j.client import Neo4jClient

from .repositories import AnalyticsRepository
from .services import AnalyticsService


class AnalyticsUseCase:
    """Orchestrates graph analytics — coordinates service (logic) + repository (DB)."""

    def __init__(self, client: Neo4jClient):
        self.service = AnalyticsService()
        self.repo = AnalyticsRepository(client)

    def run_all(self) -> dict:
        """Run the full analytics pipeline.

        Steps:
        1. Load co-authorship edges from DB
        2. Detect communities → store on Author nodes
        3. Compute centrality → store on Author nodes
        4. Compute h-index → store on Author nodes
        5. Compute trend scores → store on Method/Task nodes
        6. Compute diffusion paths → store on Method nodes

        Returns summary stats.
        """
        # Step 1: Load authored edges
        authored_edges = self.repo.get_authored_edges()
        logger.info(f"Loaded {len(authored_edges)} authored edges")

        communities_count = 0
        centrality_count = 0

        if authored_edges:
            # Step 2: Community detection
            communities = self.service.run_community_detection(authored_edges)
            if communities:
                self.repo.update_community_ids(communities, "Author")
                communities_count = len(set(communities.values()))

            # Step 3-4: Centrality + h-index
            centrality, h_indices = self.service.run_centrality(authored_edges)
            if centrality:
                self.repo.update_centrality(centrality)
                centrality_count = len(centrality)
            if h_indices:
                self.repo.update_h_index(h_indices)

        # Step 5-6: Trends + diffusion
        method_trends, task_trends, diffusion = self.service.run_trend_scoring()
        if method_trends:
            self.repo.update_trend_scores(method_trends, "Method")
        if task_trends:
            self.repo.update_trend_scores(task_trends, "Task")
        if diffusion:
            self.repo.update_diffusion_paths(diffusion)

        return {
            "communities_detected": communities_count,
            "authors_with_centrality": centrality_count,
            "methods_with_trends": len(method_trends),
            "tasks_with_trends": len(task_trends),
        }

    def get_communities(self, limit: int = 50) -> list[dict]:
        """Get community data."""
        return self.repo.get_communities(limit=limit)

    def get_trending(self, entity_type: str = "Method", limit: int = 10) -> list[dict]:
        """Get trending methods or tasks."""
        return self.repo.get_trending(entity_type, limit=limit)
