"""
Pure data parsing functions for PwC JSON files.
"""

import json
from pathlib import Path
from typing import Iterator


def load_json(path: Path) -> list:
    """Load a JSON file and return its contents."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iter_papers(
    data: list, max_papers: int = 5000, offset: int = 0, limit: int = 0
) -> Iterator[dict]:
    """Parse raw papers JSON into clean dicts.

    Args:
        data: Raw papers JSON list.
        max_papers: Max papers to consider from source data.
        offset: Skip this many *valid* items before yielding.
        limit: Yield at most this many items (0 = unlimited).
    """
    yielded = 0
    skipped = 0
    for p in data[:max_papers]:
        if not p.get("title") or not p.get("abstract"):
            continue
        if skipped < offset:
            skipped += 1
            continue
        if limit > 0 and yielded >= limit:
            return
        yield {
            "uid": p.get("paper_url", p.get("id", "")),
            "title": p["title"].strip(),
            "abstract": p["abstract"].strip()[:2000],
            "year": p.get("published", "")[:4],
            "url": p.get("paper_url", ""),
        }
        yielded += 1


def iter_methods(
    data: list, max_items: int = 0, offset: int = 0, limit: int = 0
) -> Iterator[dict]:
    """Parse raw methods JSON into clean dicts."""
    items = data[:max_items] if max_items > 0 else data
    yielded = 0
    skipped = 0
    for m in items:
        if not m.get("name"):
            continue
        if skipped < offset:
            skipped += 1
            continue
        if limit > 0 and yielded >= limit:
            return
        yield {
            "uid": m.get("id", m["name"]),
            "name": m["name"].strip(),
            "full_name": (m.get("full_name") or m["name"]).strip(),
            "description": (m.get("description") or "")[:2000],
        }
        yielded += 1


def iter_tasks(
    data: list, max_items: int = 0, offset: int = 0, limit: int = 0
) -> Iterator[dict]:
    """Parse raw tasks JSON into clean dicts."""
    items = data[:max_items] if max_items > 0 else data
    yielded = 0
    skipped = 0
    for t in items:
        if not t.get("name"):
            continue
        if skipped < offset:
            skipped += 1
            continue
        if limit > 0 and yielded >= limit:
            return
        yield {
            "uid": t.get("id", t["name"]),
            "name": t["name"].strip(),
            "area": (t.get("area") or "").strip(),
            "description": (t.get("description") or "")[:1000],
        }
        yielded += 1


def iter_datasets(
    data: list, max_items: int = 0, offset: int = 0, limit: int = 0
) -> Iterator[dict]:
    """Parse raw datasets JSON into clean dicts."""
    items = data[:max_items] if max_items > 0 else data
    yielded = 0
    skipped = 0
    for d in items:
        if not d.get("name"):
            continue
        if skipped < offset:
            skipped += 1
            continue
        if limit > 0 and yielded >= limit:
            return
        yield {
            "uid": d.get("id", d["name"]),
            "name": d["name"].strip(),
            "description": (d.get("description") or "")[:1000],
            "modalities": ", ".join(d.get("modalities") or []),
        }
        yielded += 1


def iter_authors(data: list, max_papers: int = 5000) -> Iterator[dict]:
    """Extract unique author names from papers JSON.

    Each author gets a uid derived from the normalized name.
    Yields dicts with keys: uid, name.
    De-duplicates by stripped name across all papers.
    """
    seen: set[str] = set()
    for p in data[:max_papers]:
        for raw_name in p.get("authors") or []:
            name = raw_name.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            yield {"uid": f"author:{name.lower().replace(' ', '_')}", "name": name}


def iter_author_paper_edges(
    data: list, max_papers: int = 5000
) -> Iterator[dict]:
    """Extract author-paper edges from papers JSON.

    Yields dicts with keys: author_name, paper_uid, order.
    """
    for p in data[:max_papers]:
        if not p.get("title") or not p.get("abstract"):
            continue
        paper_uid = p.get("paper_url", p.get("id", ""))
        for order, raw_name in enumerate(p.get("authors") or []):
            name = raw_name.strip()
            if not name:
                continue
            yield {
                "author_name": name,
                "paper_uid": paper_uid,
                "order": order,
            }
