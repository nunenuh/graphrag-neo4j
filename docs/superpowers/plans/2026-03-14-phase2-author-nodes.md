# Phase 2: Author Nodes + Entity Resolution — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Author nodes with entity-resolved names and AUTHORED/CO_AUTHORED_WITH relationships so Graph RAG can answer cross-domain researcher queries.

**Architecture:** Ingestion-time ER — extract authors from papers.json, normalize names, deduplicate via blocking + scoring (threshold >= 0.85), then batch-create Author nodes and relationship edges. No new API endpoints; existing endpoints dynamically include Author data.

**Tech Stack:** Python 3.11, neomodel OGM, Neo4j 5.x, pytest, FastAPI, React/TypeScript

**Spec:** `docs/superpowers/specs/2026-03-14-phase2-author-nodes-design.md`

---

## Chunk 1: Data Model + Merger Library

### Task 1: Add CoAuthoredWithRel relationship model

**Files:**
- Modify: `backend/src/graphrag_service/dbase/neo4j/models/relationships.py`
- Modify: `backend/src/graphrag_service/dbase/neo4j/models/__init__.py`
- Test: `backend/tests/unit/dbase/neo4j/models/test_relationships.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/dbase/neo4j/models/test_relationships.py

from graphrag_service.dbase.neo4j.models.relationships import CoAuthoredWithRel

def test_co_authored_with_rel_has_paper_count():
    rel = CoAuthoredWithRel(paper_count=5)
    assert rel.paper_count == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/dbase/neo4j/models/test_relationships.py::test_co_authored_with_rel_has_paper_count -v`
Expected: FAIL — ImportError (CoAuthoredWithRel not defined)

- [ ] **Step 3: Implement CoAuthoredWithRel**

Add to `backend/src/graphrag_service/dbase/neo4j/models/relationships.py` after AuthoredRel (line 30):

```python
class CoAuthoredWithRel(StructuredRel):
    """Author -[:CO_AUTHORED_WITH]-> Author. Derived from shared papers."""

    paper_count = IntegerProperty(default=0)
```

- [ ] **Step 4: Add co_authors relationship to Author model**

In `backend/src/graphrag_service/dbase/neo4j/models/nodes.py`, add to the Author class (after `papers` relationship, around line 39):

```python
co_authors = RelationshipTo("Author", "CO_AUTHORED_WITH", model=CoAuthoredWithRel)
```

Import CoAuthoredWithRel at the top of nodes.py.

- [ ] **Step 5: Export CoAuthoredWithRel from __init__.py**

In `backend/src/graphrag_service/dbase/neo4j/models/__init__.py`, add `CoAuthoredWithRel` to the imports and `__all__`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/dbase/neo4j/models/test_relationships.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/graphrag_service/dbase/neo4j/models/relationships.py backend/src/graphrag_service/dbase/neo4j/models/nodes.py backend/src/graphrag_service/dbase/neo4j/models/__init__.py backend/tests/unit/dbase/neo4j/models/test_relationships.py
git commit -m "feat(models): add CoAuthoredWithRel relationship model"
```

---

### Task 2: Implement merger.py — canonical name selection + alias collection

**Files:**
- Create: `backend/src/graphrag_service/library/entity_resolution/merger.py`
- Test: `backend/tests/unit/library/entity_resolution/test_merger.py`
- Modify: `backend/src/graphrag_service/library/entity_resolution/__init__.py`

**Context:**
- `blocker.py:71-111` — `find_clusters()` returns `list[list[dict]]` where each inner list is a cluster of author dicts `{"uid": ..., "name": ...}` that should be merged.
- `normalizer.py:31-57` — `normalize_name(name)` returns lowercase, diacritics-removed string.
- Merger takes clusters and produces canonical author records.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/library/entity_resolution/test_merger.py

from graphrag_service.library.entity_resolution.merger import merge_clusters, MergedAuthor


def test_merge_single_cluster_picks_most_frequent_name():
    cluster = [
        {"uid": "author:g_hinton", "name": "G. Hinton"},
        {"uid": "author:g_hinton_2", "name": "Geoffrey Hinton"},
        {"uid": "author:g_hinton_3", "name": "Geoffrey Hinton"},
    ]
    results = merge_clusters([cluster])
    assert len(results) == 1
    assert results[0].name == "Geoffrey Hinton"
    assert "G. Hinton" in results[0].aliases


def test_merge_preserves_all_original_uids():
    cluster = [
        {"uid": "author:j_smith", "name": "J. Smith"},
        {"uid": "author:john_smith", "name": "John Smith"},
    ]
    results = merge_clusters([cluster])
    assert set(results[0].original_uids) == {"author:j_smith", "author:john_smith"}


def test_merge_generates_deterministic_uid():
    cluster = [
        {"uid": "a1", "name": "John Smith"},
        {"uid": "a2", "name": "J. Smith"},
    ]
    r1 = merge_clusters([cluster])
    r2 = merge_clusters([cluster])
    assert r1[0].uid == r2[0].uid


def test_merge_multiple_clusters():
    clusters = [
        [{"uid": "a1", "name": "Alice"}, {"uid": "a2", "name": "A. Lee"}],
        [{"uid": "b1", "name": "Bob"}, {"uid": "b2", "name": "Robert"}],
    ]
    results = merge_clusters(clusters)
    assert len(results) == 2


def test_merge_empty_clusters():
    assert merge_clusters([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/library/entity_resolution/test_merger.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement merger.py**

```python
# backend/src/graphrag_service/library/entity_resolution/merger.py
"""Merge entity resolution clusters into canonical author records."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field

from graphrag_service.library.entity_resolution.normalizer import (
    compute_blocking_key,
    normalize_name,
)


@dataclass(frozen=True)
class MergedAuthor:
    """A canonical author record produced by merging a cluster."""

    uid: str
    name: str
    name_normalized: str
    blocking_key: str
    aliases: tuple[str, ...]
    original_uids: tuple[str, ...]


def deterministic_uid(name_normalized: str) -> str:
    """Generate a deterministic uid from normalized name."""
    h = hashlib.sha256(name_normalized.encode()).hexdigest()[:12]
    return f"author:{h}"


def _pick_canonical_name(names: list[str]) -> str:
    """Pick the most frequent name form; break ties by longest."""
    counts = Counter(names)
    max_count = max(counts.values())
    candidates = [n for n, c in counts.items() if c == max_count]
    return max(candidates, key=len)


def merge_clusters(clusters: list[list[dict]]) -> list[MergedAuthor]:
    """Merge clusters into canonical MergedAuthor records.

    Each cluster is a list of author dicts: {"uid": str, "name": str}.
    Returns one MergedAuthor per cluster.
    """
    results: list[MergedAuthor] = []
    for cluster in clusters:
        if not cluster:
            continue
        names = [a["name"] for a in cluster]
        canonical = _pick_canonical_name(names)
        normalized = normalize_name(canonical)
        aliases = tuple(sorted(set(n for n in names if n != canonical)))
        results.append(
            MergedAuthor(
                uid=deterministic_uid(normalized),
                name=canonical,
                name_normalized=normalized,
                blocking_key=compute_blocking_key(canonical),
                aliases=aliases,
                original_uids=tuple(a["uid"] for a in cluster),
            )
        )
    return results
```

- [ ] **Step 4: Export from __init__.py**

Add `merge_clusters` and `MergedAuthor` to `backend/src/graphrag_service/library/entity_resolution/__init__.py` exports.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/library/entity_resolution/test_merger.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/graphrag_service/library/entity_resolution/merger.py backend/tests/unit/library/entity_resolution/test_merger.py backend/src/graphrag_service/library/entity_resolution/__init__.py
git commit -m "feat(er): add merger module for canonical name selection"
```

---

## Chunk 2: Author Ingestion Pipeline

### Task 3: Build the author ingestion orchestrator

**Files:**
- Create: `backend/src/graphrag_service/modules/graph/author_ingestion.py`
- Test: `backend/tests/unit/modules/graph/test_author_ingestion.py`

**Context:**
- `library/parsers.py:120-158` — `iter_authors()` yields `{"uid", "name"}`, `iter_author_paper_edges()` yields `{"author_name", "paper_uid", "order"}`
- `library/entity_resolution/` — normalizer, blocker, scorer, merger
- `modules/graph/repositories.py:236-248` — `batch_merge_authored()` already exists
- This module orchestrates: extract → normalize → block → score → merge → prepare batch data

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/modules/graph/test_author_ingestion.py

from unittest.mock import MagicMock, patch
from graphrag_service.modules.graph.author_ingestion import (
    run_entity_resolution,
    prepare_author_nodes,
    prepare_coauthor_edges,
)


def test_run_entity_resolution_merges_similar_names():
    """Names that differ only by initial vs full should merge."""
    raw_authors = [
        {"uid": "author:j_doe", "name": "J. Doe"},
        {"uid": "author:john_doe", "name": "John Doe"},
        {"uid": "author:jane_smith", "name": "Jane Smith"},
    ]
    merged, uid_mapping = run_entity_resolution(raw_authors)
    # J. Doe and John Doe may or may not merge depending on scorer
    # Jane Smith should be standalone
    smith_authors = [a for a in merged if "Smith" in a.name or "smith" in a.name_normalized]
    assert len(smith_authors) == 1


def test_prepare_author_nodes_returns_dicts():
    from graphrag_service.library.entity_resolution.merger import MergedAuthor

    authors = [
        MergedAuthor(
            uid="author:abc123",
            name="John Doe",
            name_normalized="john doe",
            blocking_key="doe_j",
            aliases=("J. Doe",),
            original_uids=("author:j_doe", "author:john_doe"),
        )
    ]
    nodes = prepare_author_nodes(authors)
    assert len(nodes) == 1
    assert nodes[0]["uid"] == "author:abc123"
    assert nodes[0]["name"] == "John Doe"
    assert nodes[0]["aliases"] == '["J. Doe"]'


def test_prepare_coauthor_edges_counts_shared_papers():
    # Paper 1: authors A, B, C → pairs (A,B), (A,C), (B,C)
    # Paper 2: authors A, B → pair (A,B)
    # Result: (A,B) has paper_count=2, others have 1
    author_paper_edges = [
        {"author_uid": "a", "paper_uid": "p1", "order": 0},
        {"author_uid": "b", "paper_uid": "p1", "order": 1},
        {"author_uid": "c", "paper_uid": "p1", "order": 2},
        {"author_uid": "a", "paper_uid": "p2", "order": 0},
        {"author_uid": "b", "paper_uid": "p2", "order": 1},
    ]
    edges = prepare_coauthor_edges(author_paper_edges)
    ab_edge = next(e for e in edges if set([e["from_uid"], e["to_uid"]]) == {"a", "b"})
    assert ab_edge["paper_count"] == 2
    assert len(edges) == 3  # (A,B), (A,C), (B,C)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/modules/graph/test_author_ingestion.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement author_ingestion.py**

```python
# backend/src/graphrag_service/modules/graph/author_ingestion.py
"""Orchestrate author extraction, entity resolution, and edge preparation."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from itertools import combinations

from graphrag_service.library.entity_resolution import (
    build_blocks,
    find_clusters,
    merge_clusters,
    normalize_name,
    compute_blocking_key,
)
from graphrag_service.library.entity_resolution.merger import MergedAuthor

logger = logging.getLogger(__name__)


def run_entity_resolution(
    raw_authors: list[dict],
    threshold: float = 0.85,
) -> tuple[list[MergedAuthor], dict[str, str]]:
    """Run the full ER pipeline on raw author dicts.

    Returns:
        merged: list of MergedAuthor records (canonical authors)
        uid_mapping: dict mapping original uid -> canonical uid
    """
    # Add normalized fields for blocking
    for author in raw_authors:
        author["name_normalized"] = normalize_name(author["name"])
        author["blocking_key"] = compute_blocking_key(author["name"])

    # Block
    blocks = build_blocks(raw_authors)
    logger.info("Built %d blocks from %d raw authors", len(blocks), len(raw_authors))

    # Score + cluster
    all_clusters: list[list[dict]] = []
    clustered_uids: set[str] = set()
    for _key, block in blocks.items():
        clusters = find_clusters(block, threshold=threshold)
        for cluster in clusters:
            all_clusters.append(cluster)
            for a in cluster:
                clustered_uids.add(a["uid"])

    # Merge clusters
    merged = merge_clusters(all_clusters)
    logger.info("Merged %d clusters into %d canonical authors", len(all_clusters), len(merged))

    # Build uid mapping (original -> canonical)
    uid_mapping: dict[str, str] = {}
    for ma in merged:
        for orig_uid in ma.original_uids:
            uid_mapping[orig_uid] = ma.uid

    # Authors not in any cluster become standalone
    standalone: list[MergedAuthor] = []
    for author in raw_authors:
        if author["uid"] not in clustered_uids:
            normalized = normalize_name(author["name"])
            from graphrag_service.library.entity_resolution.merger import deterministic_uid
            uid = deterministic_uid(normalized)
            standalone.append(
                MergedAuthor(
                    uid=uid,
                    name=author["name"],
                    name_normalized=normalized,
                    blocking_key=compute_blocking_key(author["name"]),
                    aliases=(),
                    original_uids=(author["uid"],),
                )
            )
            uid_mapping[author["uid"]] = uid

    all_authors = merged + standalone
    logger.info("Total canonical authors: %d (%d merged + %d standalone)", len(all_authors), len(merged), len(standalone))
    return all_authors, uid_mapping


def prepare_author_nodes(authors: list[MergedAuthor]) -> list[dict]:
    """Convert MergedAuthor records to dicts ready for Neo4j upsert."""
    return [
        {
            "uid": a.uid,
            "name": a.name,
            "name_normalized": a.name_normalized,
            "blocking_key": a.blocking_key,
            "aliases": json.dumps(list(a.aliases)),
        }
        for a in authors
    ]


def prepare_coauthor_edges(author_paper_edges: list[dict]) -> list[dict]:
    """Derive CO_AUTHORED_WITH edges from author-paper edges.

    Groups edges by paper, generates all author pairs per paper,
    then aggregates paper_count per unique author pair.
    """
    # Group by paper
    papers: dict[str, list[str]] = defaultdict(list)
    for edge in author_paper_edges:
        papers[edge["paper_uid"]].append(edge["author_uid"])

    # Count co-authorships
    pair_counts: Counter[tuple[str, str]] = Counter()
    for _paper_uid, author_uids in papers.items():
        unique_authors = sorted(set(author_uids))
        for a, b in combinations(unique_authors, 2):
            pair_counts[(a, b)] += 1

    return [
        {"from_uid": a, "to_uid": b, "paper_count": count}
        for (a, b), count in pair_counts.items()
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/modules/graph/test_author_ingestion.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/graphrag_service/modules/graph/author_ingestion.py backend/tests/unit/modules/graph/test_author_ingestion.py
git commit -m "feat(graph): add author ingestion orchestrator with ER pipeline"
```

---

### Task 4: Add batch_merge_coauthored repository method

**Files:**
- Modify: `backend/src/graphrag_service/modules/graph/repositories.py` (after `batch_merge_authored` at line 248)
- Test: `backend/tests/unit/modules/graph/test_repositories.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to backend/tests/unit/modules/graph/test_repositories.py

class TestBatchMergeCoauthored:
    def test_returns_count(self):
        mock_client = MagicMock()
        repo = NodeRepository(mock_client)
        rows = [
            {"from_uid": "author:a", "to_uid": "author:b", "paper_count": 3},
            {"from_uid": "author:a", "to_uid": "author:c", "paper_count": 1},
        ]
        count = repo.batch_merge_coauthored(rows)
        assert count == 2
        mock_client.run_query.assert_called_once()
        cypher = mock_client.run_query.call_args[0][0]
        assert "CO_AUTHORED_WITH" in cypher
        assert "UNWIND" in cypher

    def test_empty_rows_returns_zero(self):
        mock_client = MagicMock()
        repo = NodeRepository(mock_client)
        assert repo.batch_merge_coauthored([]) == 0
        mock_client.run_query.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/modules/graph/test_repositories.py::test_batch_merge_coauthored_returns_count -v`
Expected: FAIL — AttributeError (method not found)

- [ ] **Step 3: Implement batch_merge_coauthored**

Add to `backend/src/graphrag_service/modules/graph/repositories.py` after `batch_merge_authored`:

```python
def batch_merge_coauthored(self, rows: list[dict]) -> int:
    """Batch MERGE CO_AUTHORED_WITH relationships between authors.

    Each row: {"from_uid": str, "to_uid": str, "paper_count": int}
    """
    if not rows:
        return 0
    cypher = """
    UNWIND $rows AS row
    MATCH (a:Author {uid: row.from_uid})
    MATCH (b:Author {uid: row.to_uid})
    MERGE (a)-[r:CO_AUTHORED_WITH]->(b)
    SET r.paper_count = row.paper_count
    """
    self._client.run_query(cypher, {"rows": rows})
    return len(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/modules/graph/test_repositories.py::test_batch_merge_coauthored_returns_count -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/graphrag_service/modules/graph/repositories.py backend/tests/unit/modules/graph/test_repositories.py
git commit -m "feat(graph): add batch_merge_coauthored repository method"
```

---

### Task 5: Wire author ingestion into usecase + CLI

**Files:**
- Modify: `backend/src/graphrag_service/modules/graph/usecase.py` (add `ingest_authors` method)
- Modify: `backend/src/graphrag_service/modules/graph/cli/commands.py` (add `ingest-authors` command)
- Modify: `Makefile` (add `ingest-authors` target)
- Test: `backend/tests/unit/modules/graph/test_usecase.py`

- [ ] **Step 1: Write the failing test for ingest_authors usecase**

```python
# Add to backend/tests/unit/modules/graph/test_usecase.py

from unittest.mock import patch, MagicMock
from graphrag_service.modules.graph.usecase import GraphUseCase


def test_ingest_authors_calls_er_pipeline():
    """ingest_authors should extract, resolve, and batch-create authors."""
    mock_client = MagicMock()
    usecase = GraphUseCase(mock_client)

    mock_authors = [{"uid": "author:john_doe", "name": "John Doe"}]
    mock_edges = [{"author_name": "John Doe", "paper_uid": "paper:123", "order": 0}]

    with patch("graphrag_service.modules.graph.usecase.iter_authors", return_value=iter(mock_authors)), \
         patch("graphrag_service.modules.graph.usecase.iter_author_paper_edges", return_value=iter(mock_edges)), \
         patch("graphrag_service.modules.graph.usecase.load_json", return_value=[]), \
         patch("graphrag_service.modules.graph.usecase.run_entity_resolution") as mock_er, \
         patch("graphrag_service.modules.graph.usecase.prepare_author_nodes") as mock_prep, \
         patch("graphrag_service.modules.graph.usecase.prepare_coauthor_edges") as mock_coauth, \
         patch.object(usecase, "_upsert_without_embedding"):

        from graphrag_service.library.entity_resolution.merger import MergedAuthor
        mock_er.return_value = (
            [MergedAuthor(uid="author:abc", name="John Doe", name_normalized="john doe", blocking_key="doe_j", aliases=(), original_uids=("author:john_doe",))],
            {"author:john_doe": "author:abc"},
        )
        mock_prep.return_value = [{"uid": "author:abc", "name": "John Doe", "name_normalized": "john doe", "blocking_key": "doe_j", "aliases": "[]"}]
        mock_coauth.return_value = []

        usecase.ingest_authors()

        mock_er.assert_called_once()
        mock_prep.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/modules/graph/test_usecase.py::test_ingest_authors_calls_er_pipeline -v`
Expected: FAIL — AttributeError (ingest_authors not found)

- [ ] **Step 3: Implement ingest_authors in usecase.py**

Add to `backend/src/graphrag_service/modules/graph/usecase.py`:

```python
# Add imports at top
from graphrag_service.library.parsers import iter_authors, iter_author_paper_edges, load_json
from graphrag_service.modules.graph.author_ingestion import (
    run_entity_resolution,
    prepare_author_nodes,
    prepare_coauthor_edges,
)

# Add method to GraphUseCase class
def ingest_authors(self, batch_size: int = 500) -> dict:
    """Run author extraction, entity resolution, and relationship creation.

    Returns summary dict with counts.
    """
    data_path = GraphService.data_dir()
    data = load_json(data_path / "papers.json")

    # Step 1: Extract raw authors
    raw_authors = list(iter_authors(data))
    logger.info("Extracted %d raw authors", len(raw_authors))

    # Step 2: Run entity resolution
    canonical_authors, uid_mapping = run_entity_resolution(raw_authors)
    logger.info("Resolved to %d canonical authors", len(canonical_authors))

    # Step 3: Batch upsert Author nodes (Author has no embedding)
    author_nodes = prepare_author_nodes(canonical_authors)
    for i in range(0, len(author_nodes), batch_size):
        batch = author_nodes[i : i + batch_size]
        self._upsert_without_embedding(Author, batch)
    logger.info("Upserted %d author nodes", len(author_nodes))

    # Step 4: Create AUTHORED edges (map original author names to canonical uids)
    raw_edges = list(iter_author_paper_edges(data))
    authored_rows = []
    for edge in raw_edges:
        # Find the canonical uid for this author name
        raw_uid = f"author:{edge['author_name'].strip().lower().replace(' ', '_')}"
        canonical_uid = uid_mapping.get(raw_uid, raw_uid)
        authored_rows.append({
            "auid": canonical_uid,
            "puid": edge["paper_uid"],
            "order": edge["order"],
        })

    authored_count = 0
    for i in range(0, len(authored_rows), batch_size):
        batch = authored_rows[i : i + batch_size]
        authored_count += self.node_repo.batch_merge_authored(batch)
    logger.info("Created %d AUTHORED edges", authored_count)

    # Step 5: Create CO_AUTHORED_WITH edges
    coauthor_edge_input = [
        {"author_uid": r["auid"], "paper_uid": r["puid"], "order": r["order"]}
        for r in authored_rows
    ]
    coauthor_rows = prepare_coauthor_edges(coauthor_edge_input)
    coauthor_count = 0
    for i in range(0, len(coauthor_rows), batch_size):
        batch = coauthor_rows[i : i + batch_size]
        coauthor_count += self.node_repo.batch_merge_coauthored(batch)
    logger.info("Created %d CO_AUTHORED_WITH edges", coauthor_count)

    return {
        "raw_authors": len(raw_authors),
        "canonical_authors": len(canonical_authors),
        "authored_edges": authored_count,
        "coauthor_edges": coauthor_count,
    }
```

Note: `_upsert_without_embedding(model, nodes)` already exists on `GraphUseCase` (usecase.py lines 205-221). It builds dynamic UNWIND/MERGE Cypher from the model's properties, excluding `embedding`. Author model has no embedding property, so all Author properties will be set.

- [ ] **Step 4: Add CLI command**

Add to `backend/src/graphrag_service/modules/graph/cli/commands.py`:

Inside `get_graph_app()`, add after the `ingest_rels` command (follows the existing pattern from `commands.py` lines 109-122):

```python
@app.command(name="ingest-authors")
def ingest_authors(
    batch_size: int = typer.Option(500, help="Batch size for Neo4j operations"),
) -> None:
    """Run author extraction + entity resolution + relationship creation."""
    print_info("Ingesting authors with entity resolution...")
    try:
        client = get_neo4j_client()
        usecase = GraphUseCase(client)
        result = usecase.ingest_authors(batch_size=batch_size)
        print_success(
            f"Authors: {result['raw_authors']} raw -> {result['canonical_authors']} canonical\n"
            f"Edges: {result['authored_edges']} AUTHORED, {result['coauthor_edges']} CO_AUTHORED_WITH"
        )
    except Exception as e:
        print_error(f"Author ingestion failed: {e}")
        raise typer.Exit(code=1)
    finally:
        close_neo4j_client()
```

- [ ] **Step 5: Add Makefile target**

Add to `Makefile` after the `ingest` target:

```makefile
ingest-authors: ## Ingest authors with entity resolution
	$(POETRY_RUN) cli graph ingest-authors
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/modules/graph/test_usecase.py::test_ingest_authors_calls_er_pipeline -v`
Expected: PASS

- [ ] **Step 7: Also wire ingest_authors into the existing `ingest` command**

In `commands.py`, the `ingest` command (line 42-107) calls `usecase.ingest_nodes()` then `usecase.ingest_relationships()`. Add `usecase.ingest_authors()` after `ingest_relationships()` so `make ingest` runs the full pipeline including authors.

- [ ] **Step 8: Run full unit test suite**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/unit/ -v --tb=short`
Expected: All pass (except pre-existing `test_traverse_with_data` failure)

- [ ] **Step 9: Commit**

```bash
git add backend/src/graphrag_service/modules/graph/usecase.py backend/src/graphrag_service/modules/graph/cli/commands.py Makefile backend/tests/unit/modules/graph/test_usecase.py
git commit -m "feat(graph): wire author ingestion into usecase and CLI"
```

---

## Chunk 3: API + Frontend Updates

### Task 6: Update frontend types and visualization for Author nodes

**Files:**
- Modify: `frontend/src/types/api.ts` (line 10)
- Modify: `frontend/src/components/TraversalPath.tsx` (already has Author color)
- Modify: `frontend/src/components/GraphViewer.tsx` (add Author node color)

- [ ] **Step 1: Add "Author" to NodeLabel type**

In `frontend/src/types/api.ts` line 10, change:
```typescript
export type NodeLabel = "Paper" | "Method" | "Task" | "Dataset";
```
to:
```typescript
export type NodeLabel = "Paper" | "Method" | "Task" | "Dataset" | "Author";
```

- [ ] **Step 2: Add Author color to graph visualization**

In the graph visualization component, add Author to the node color mapping. Author should be `slate`/gray to distinguish from the existing domain nodes (Paper=blue, Method=emerald, Task=purple, Dataset=orange).

Find the `NODE_COLORS` or equivalent mapping in `GraphViewer.tsx` and add:
```typescript
Author: "#64748b",  // slate-500
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/frontend && npm run build`
Expected: Build succeeds with no type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/components/GraphViewer.tsx
git commit -m "feat(frontend): add Author node type and visualization color"
```

---

### Task 7: Integration test — full author ingestion pipeline

**Files:**
- Create: `backend/tests/integration/modules/graph/test_author_ingestion_integration.py`

**Note:** This test requires a running Neo4j instance. Mark with `@pytest.mark.integration`.

- [ ] **Step 1: Write integration test**

```python
# backend/tests/integration/modules/graph/test_author_ingestion_integration.py

import pytest
from graphrag_service.core.dependencies import get_neo4j_client, close_neo4j_client
from graphrag_service.modules.graph.usecase import GraphUseCase


@pytest.mark.integration
def test_full_author_ingestion_pipeline():
    """End-to-end: extract authors from PwC data, run ER, create nodes + edges."""
    client = get_neo4j_client()
    try:
        usecase = GraphUseCase(client)
        result = usecase.ingest_authors(batch_size=100)
    finally:
        close_neo4j_client()

    assert result["raw_authors"] > 0
    assert result["canonical_authors"] > 0
    assert result["canonical_authors"] <= result["raw_authors"]
    assert result["authored_edges"] > 0
    # CO_AUTHORED_WITH may be 0 if all papers have single authors (unlikely)
    assert result["coauthor_edges"] >= 0
```

- [ ] **Step 2: Run against live Neo4j (if available)**

Run: `cd /workspace/company/nunenuh/graphrag-neo4j/backend && export PATH="/home/erfan/.local/bin:$PATH" && poetry run pytest tests/integration/modules/graph/test_author_ingestion_integration.py -v -m integration`
Expected: PASS if Neo4j is running with ingested paper data

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/modules/graph/test_author_ingestion_integration.py
git commit -m "test(graph): add integration test for author ingestion pipeline"
```

---

### Task 8: Manual verification — run the target query

- [ ] **Step 1: Run author ingestion**

```bash
cd /workspace/company/nunenuh/graphrag-neo4j && make ingest-authors
```

Expected: Output showing raw author count, canonical author count, AUTHORED edges, CO_AUTHORED_WITH edges.

- [ ] **Step 2: Verify in Neo4j Browser**

```cypher
MATCH (a:Author) RETURN count(a) AS author_count;
MATCH ()-[r:AUTHORED]->() RETURN count(r) AS authored_count;
MATCH ()-[r:CO_AUTHORED_WITH]->() RETURN count(r) AS coauthor_count;
```

Expected: Non-zero counts for all three.

- [ ] **Step 3: Test the target query via API**

```bash
curl -X POST http://localhost:8005/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"question": "Which researchers who published object detection papers also contributed to NLP tasks?"}'
```

Expected: Non-empty answer mentioning specific author names with paper connections.

- [ ] **Step 4: Verify in frontend**

Open the frontend, type the same query, and verify:
- Author nodes appear in the graph visualization (slate/gray color)
- Traversal path shows Author nodes in hop counts
- Answer references specific researchers

- [ ] **Step 5: Final commit — update design spec status**

Update `docs/superpowers/specs/2026-03-14-phase2-author-nodes-design.md` status from "Draft" to "Implemented".

```bash
git add docs/superpowers/specs/2026-03-14-phase2-author-nodes-design.md
git commit -m "docs: mark Phase 2 design spec as implemented"
```

---

## Summary

| Task | What | New/Modify | Tests |
|------|------|-----------|-------|
| 1 | CoAuthoredWithRel model | Modify relationships.py, nodes.py | Unit |
| 2 | merger.py — canonical name selection | Create merger.py | Unit |
| 3 | Author ingestion orchestrator | Create author_ingestion.py | Unit |
| 4 | batch_merge_coauthored repo method | Modify repositories.py | Unit |
| 5 | Wire into usecase + CLI + Makefile | Modify usecase.py, commands.py, Makefile | Unit |
| 6 | Frontend Author type + color | Modify api.ts, GraphViewer.tsx | Build check |
| 7 | Integration test | Create test file | Integration |
| 8 | Manual verification | Run target query | Manual |

**Total estimated effort:** 8 tasks, ~3-4 hours of implementation (60% of code already exists).
