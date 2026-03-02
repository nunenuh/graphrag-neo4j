from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
        )

    def close(self):
        self._driver.close()

    def verify_connection(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def run_query(self, cypher: str, params: dict | None = None):
        with self._driver.session() as session:
            return list(session.run(cypher, params or {}))
