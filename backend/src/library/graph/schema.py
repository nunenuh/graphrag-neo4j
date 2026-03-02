from dbase.neo4j.client import Neo4jClient
from core.config import settings

CONSTRAINTS = [
    "CREATE CONSTRAINT paper_id   IF NOT EXISTS FOR (p:Paper)   REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT method_id  IF NOT EXISTS FOR (m:Method)  REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT task_id    IF NOT EXISTS FOR (t:Task)    REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
]

VECTOR_INDEXES = [
    ("paper_embeddings",   "Paper",   "embedding"),
    ("method_embeddings",  "Method",  "embedding"),
    ("task_embeddings",    "Task",    "embedding"),
    ("dataset_embeddings", "Dataset", "embedding"),
]


def create_schema(client: Neo4jClient):
    for constraint in CONSTRAINTS:
        client.run_query(constraint)
        print(f"✓ {constraint[:60]}...")

    for name, label, prop in VECTOR_INDEXES:
        client.run_query(f"""
            CREATE VECTOR INDEX {name} IF NOT EXISTS
            FOR (n:{label}) ON (n.{prop})
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {settings.embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}}}
        """)
        print(f"✓ Vector index: {name}")


if __name__ == "__main__":
    client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    create_schema(client)
    print("Schema setup complete.")
