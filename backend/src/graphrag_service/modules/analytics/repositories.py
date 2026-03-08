"""Analytics repositories — Neo4j operations for storing computed metrics."""

from loguru import logger

from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException


class AnalyticsRepository:
    """Encapsulates Neo4j operations for analytics data."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def get_authored_edges(self) -> list[dict]:
        """Get all AUTHORED relationships for co-authorship graph building."""
        cypher = (
            "MATCH (a:Author)-[:AUTHORED]->(p:Paper) "
            "WHERE a.merged_into IS NULL "
            "RETURN a.uid AS author_uid, p.uid AS paper_uid"
        )
        try:
            return self._client.run_query(cypher)
        except Exception as e:
            raise RepositoryException(f"Failed to get authored edges: {e}") from e

    def update_community_ids(self, assignments: dict[str, int], label: str) -> None:
        """Batch update community_id on nodes."""
        rows = [{"uid": uid, "cid": cid} for uid, cid in assignments.items()]
        cypher = (
            f"UNWIND $rows AS row "
            f"MATCH (n:{label} {{uid: row.uid}}) "
            f"SET n.community_id = row.cid"
        )
        try:
            self._client.run_query(cypher, {"rows": rows})
        except Exception as e:
            raise RepositoryException(f"Failed to update community_ids: {e}") from e

    def update_centrality(self, metrics: dict[str, dict[str, float]]) -> None:
        """Batch update pagerank and betweenness on Author nodes."""
        rows = [
            {"uid": uid, "pr": m["pagerank"], "bt": m["betweenness"]}
            for uid, m in metrics.items()
        ]
        cypher = (
            "UNWIND $rows AS row "
            "MATCH (a:Author {uid: row.uid}) "
            "SET a.pagerank = row.pr, a.betweenness = row.bt"
        )
        try:
            self._client.run_query(cypher, {"rows": rows})
        except Exception as e:
            raise RepositoryException(f"Failed to update centrality: {e}") from e

    def update_h_index(self, h_indices: dict[str, int]) -> None:
        """Batch update h_index on Author nodes."""
        rows = [{"uid": uid, "h": h} for uid, h in h_indices.items()]
        cypher = (
            "UNWIND $rows AS row "
            "MATCH (a:Author {uid: row.uid}) "
            "SET a.h_index = row.h"
        )
        try:
            self._client.run_query(cypher, {"rows": rows})
        except Exception as e:
            raise RepositoryException(f"Failed to update h_index: {e}") from e

    def update_trend_scores(self, scores: dict[str, float], label: str) -> None:
        """Batch update trend_score on Method or Task nodes."""
        rows = [{"name": name, "score": s} for name, s in scores.items()]
        cypher = (
            f"UNWIND $rows AS row "
            f"MATCH (n:{label} {{name: row.name}}) "
            f"SET n.trend_score = row.score"
        )
        try:
            self._client.run_query(cypher, {"rows": rows})
        except Exception as e:
            raise RepositoryException(f"Failed to update trend scores: {e}") from e

    def update_diffusion_paths(self, paths: dict[str, str]) -> None:
        """Batch update diffusion_path on Method nodes."""
        rows = [{"name": name, "path": p} for name, p in paths.items()]
        cypher = (
            "UNWIND $rows AS row "
            "MATCH (m:Method {name: row.name}) "
            "SET m.diffusion_path = row.path"
        )
        try:
            self._client.run_query(cypher, {"rows": rows})
        except Exception as e:
            raise RepositoryException(f"Failed to update diffusion paths: {e}") from e

    def get_communities(self, limit: int = 50) -> list[dict]:
        """Get community summary data."""
        cypher = (
            "MATCH (a:Author) WHERE a.community_id IS NOT NULL "
            "WITH a.community_id AS cid, collect({uid: a.uid, name: a.name, pagerank: a.pagerank}) AS members "
            "RETURN cid, size(members) AS member_count, "
            "       [m IN members | m][..5] AS top_members "
            "ORDER BY member_count DESC LIMIT $limit"
        )
        try:
            return self._client.run_query(cypher, {"limit": limit})
        except Exception as e:
            raise RepositoryException(f"Failed to get communities: {e}") from e

    def get_trending(self, label: str, limit: int = 10) -> list[dict]:
        """Get top trending methods or tasks."""
        cypher = (
            f"MATCH (n:{label}) WHERE n.trend_score IS NOT NULL "
            f"RETURN n.uid AS uid, n.name AS name, n.trend_score AS trend_score "
            f"ORDER BY n.trend_score DESC LIMIT $limit"
        )
        try:
            return self._client.run_query(cypher, {"limit": limit})
        except Exception as e:
            raise RepositoryException(f"Failed to get trending {label}: {e}") from e
