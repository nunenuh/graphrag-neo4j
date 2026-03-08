"""
Neo4j database client — wraps neomodel connection management.
"""

from neomodel import db, get_config

from graphrag_service.core.config import get_settings
from loguru import logger



class Neo4jClient:
    """Neo4j client using neomodel for connection and query execution."""

    def __init__(self) -> None:
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """Configure neomodel connection from application settings."""
        settings = get_settings()
        host = settings.NEO4J_URI.replace("bolt://", "").replace("neo4j://", "")
        config = get_config()
        config.database_url = f"bolt://{settings.NEO4J_USER}:{settings.NEO4J_PASSWORD}@{host}"
        self._connected = True
        logger.bind(uri=settings.NEO4J_URI).info("Neomodel connection configured")

    def close(self) -> None:
        """Close the neomodel connection."""
        if self._connected:
            db.close_connection()
            self._connected = False
            logger.info("Neomodel connection closed")

    def verify_connection(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            db.cypher_query("RETURN 1")
            return True
        except Exception as e:
            logger.bind(error=str(e)).error("Neo4j connectivity check failed")
            return False

    def install_labels(self) -> None:
        """Install all neomodel labels, constraints, and indexes in Neo4j."""
        db.install_all_labels()
        logger.info("Neomodel labels installed")

    def run_query(self, cypher: str, params: dict | None = None) -> list:
        """Execute a raw Cypher query and return results.

        Uses neomodel's db.cypher_query under the hood.
        Returns list of dicts for compatibility with existing repositories.
        """
        import time

        t0 = time.perf_counter()
        results, meta = db.cypher_query(cypher, params or {})
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.bind(duration_ms=duration_ms, rows=len(results)).debug("neo4j.query")
        if not meta:
            return results
        return [dict(zip(meta, row)) for row in results]
