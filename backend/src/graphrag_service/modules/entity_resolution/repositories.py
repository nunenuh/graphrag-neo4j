"""Entity resolution repositories — Neo4j operations for Author nodes."""

import json

from loguru import logger

from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException


class AuthorRepository:
    """Encapsulates all Neo4j operations for Author nodes and AUTHORED relationships."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def upsert_authors_batch(self, authors: list[dict]) -> None:
        """Batch upsert Author nodes.

        Each author dict must have: uid, name, name_normalized, blocking_key.
        """
        cypher = (
            "UNWIND $rows AS row "
            "MERGE (a:Author {uid: row.uid}) "
            "SET a.name = row.name, "
            "    a.name_normalized = row.name_normalized, "
            "    a.blocking_key = row.blocking_key, "
            "    a.aliases = row.aliases"
        )
        try:
            self._client.run_query(cypher, {"rows": authors})
        except Exception as e:
            raise RepositoryException(f"Failed to upsert Author batch: {e}") from e

    def merge_authored_batch(self, edges: list[dict]) -> None:
        """Batch MERGE AUTHORED relationships.

        Each edge dict must have: author_uid, paper_uid, order.
        """
        cypher = (
            "UNWIND $rows AS row "
            "MATCH (a:Author {uid: row.author_uid}) "
            "MATCH (p:Paper {uid: row.paper_uid}) "
            "MERGE (a)-[r:AUTHORED]->(p) "
            "SET r.order = row.order"
        )
        try:
            self._client.run_query(cypher, {"rows": edges})
        except Exception as e:
            raise RepositoryException(f"Failed to merge AUTHORED batch: {e}") from e

    def get_all_authors(self) -> list[dict]:
        """Get all non-merged Author nodes for resolution."""
        cypher = (
            "MATCH (a:Author) "
            "WHERE a.merged_into IS NULL "
            "RETURN a.uid AS uid, a.name AS name, "
            "       a.name_normalized AS name_normalized, "
            "       a.blocking_key AS blocking_key, "
            "       a.aliases AS aliases"
        )
        try:
            return self._client.run_query(cypher)
        except Exception as e:
            raise RepositoryException(f"Failed to get authors: {e}") from e

    def merge_authors(self, canonical_uid: str, merged_uids: list[str], aliases: list[str]) -> None:
        """Merge duplicate authors into a canonical author.

        - Sets merged_into on duplicate nodes
        - Moves AUTHORED rels from duplicates to canonical
        - Updates aliases on canonical
        """
        # Mark duplicates
        cypher_mark = (
            "UNWIND $uids AS uid "
            "MATCH (a:Author {uid: uid}) "
            "SET a.merged_into = $canonical_uid"
        )
        # Move relationships
        cypher_move = (
            "UNWIND $uids AS uid "
            "MATCH (dup:Author {uid: uid})-[r:AUTHORED]->(p:Paper) "
            "MATCH (canon:Author {uid: $canonical_uid}) "
            "MERGE (canon)-[nr:AUTHORED]->(p) "
            "SET nr.order = r.order "
            "DELETE r"
        )
        # Update aliases on canonical
        cypher_aliases = (
            "MATCH (a:Author {uid: $canonical_uid}) "
            "SET a.aliases = $aliases"
        )
        try:
            self._client.run_query(cypher_mark, {"uids": merged_uids, "canonical_uid": canonical_uid})
            self._client.run_query(cypher_move, {"uids": merged_uids, "canonical_uid": canonical_uid})
            self._client.run_query(cypher_aliases, {"canonical_uid": canonical_uid, "aliases": json.dumps(aliases)})
        except Exception as e:
            raise RepositoryException(f"Failed to merge authors: {e}") from e

    def get_stats(self) -> dict:
        """Get entity resolution statistics."""
        try:
            total = self._client.run_query("MATCH (a:Author) RETURN count(a) AS c")
            merged = self._client.run_query(
                "MATCH (a:Author) WHERE a.merged_into IS NOT NULL RETURN count(a) AS c"
            )
            rels = self._client.run_query("MATCH ()-[r:AUTHORED]->() RETURN count(r) AS c")
            return {
                "total_authors": total[0]["c"] if total else 0,
                "merged_authors": merged[0]["c"] if merged else 0,
                "total_authored_rels": rels[0]["c"] if rels else 0,
            }
        except Exception as e:
            raise RepositoryException(f"Failed to get ER stats: {e}") from e
