"""
FastAPI dependency injection for shared resources.
"""

from graphrag_service.dbase.neo4j.client import Neo4jClient

_neo4j_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client


def close_neo4j_client() -> None:
    """Close Neo4j client connection."""
    global _neo4j_client
    if _neo4j_client is not None:
        _neo4j_client.close()
        _neo4j_client = None
