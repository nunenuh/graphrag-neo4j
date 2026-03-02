"""
Load all entities into Neo4j with embeddings.
Run once: poetry run python src/library/graph/ingest.py
Expected: ~30 min (embedding API calls)
"""
import json
from pathlib import Path
from tqdm import tqdm
from dbase.neo4j.client import Neo4jClient
from core.config import settings
from library.graph.parser import iter_papers, iter_methods, iter_tasks, iter_datasets
from library.rag.embedder import embed_batch

BATCH = 50


def _upsert_nodes(client: Neo4jClient, label: str, nodes: list[dict]):
    texts = [
        f"{n.get('title', n.get('name', ''))} {n.get('abstract', n.get('description', ''))}"
        for n in nodes
    ]
    embeddings = embed_batch(texts)
    records = [{**node, "embedding": emb} for node, emb in zip(nodes, embeddings)]
    props = list(nodes[0].keys()) + ["embedding"]
    set_clause = " ".join([f"n.{p} = row.{p}," for p in props]).rstrip(",")
    client.run_query(
        f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET {set_clause}",
        {"rows": records},
    )


def ingest_all(client: Neo4jClient):
    for label, iterator in [
        ("Paper",   iter_papers),
        ("Method",  iter_methods),
        ("Task",    iter_tasks),
        ("Dataset", iter_datasets),
    ]:
        print(f"Ingesting {label}s...")
        batch = []
        for node in tqdm(iterator()):
            batch.append(node)
            if len(batch) == BATCH:
                _upsert_nodes(client, label, batch)
                batch = []
        if batch:
            _upsert_nodes(client, label, batch)
        print(f"✓ {label} done")


def ingest_relationships(client: Neo4jClient):
    print("Ingesting relationships...")
    with open(Path("../data/evaluations.json")) as f:
        evals = json.load(f)
    for ev in tqdm(evals[:10000]):
        task_name    = ev.get("task",    {}).get("task_name",    "")
        dataset_name = ev.get("dataset", {}).get("dataset_name", "")
        if not task_name or not dataset_name:
            continue
        client.run_query(
            "MERGE (t:Task {id: $id}) ON CREATE SET t.name = $name",
            {"id": task_name, "name": task_name},
        )
        client.run_query("""
            MATCH (d:Dataset {name: $dname})
            MATCH (t:Task    {name: $tname})
            MERGE (d)-[:USED_FOR]->(t)
        """, {"dname": dataset_name, "tname": task_name})
        for row in ev.get("sota_rows", [])[:5]:
            method_name = row.get("method_name", "")
            if not method_name:
                continue
            for metric in row.get("metrics", []):
                client.run_query("""
                    MATCH (m:Method  {name: $mname})
                    MATCH (d:Dataset {name: $dname})
                    MERGE (m)-[r:EVALUATED_ON {metric: $metric}]->(d)
                    SET r.score = $score
                """, {
                    "mname":  method_name,
                    "dname":  dataset_name,
                    "metric": metric.get("metric", ""),
                    "score":  str(metric.get("value", "")),
                })
    print("✓ Relationships done")


if __name__ == "__main__":
    client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    ingest_all(client)
    ingest_relationships(client)
    print("\n✅ Ingestion complete.")
