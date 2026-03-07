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


def iter_papers(data: list, max_papers: int = 5000) -> Iterator[dict]:
    """Parse raw papers JSON into clean dicts."""
    for p in data[:max_papers]:
        if not p.get("title") or not p.get("abstract"):
            continue
        yield {
            "uid": p.get("paper_url", p.get("id", "")),
            "title": p["title"].strip(),
            "abstract": p["abstract"].strip()[:2000],
            "year": p.get("published", "")[:4],
            "url": p.get("paper_url", ""),
        }


def iter_methods(data: list, max_items: int = 0) -> Iterator[dict]:
    """Parse raw methods JSON into clean dicts."""
    items = data[:max_items] if max_items > 0 else data
    for m in items:
        if not m.get("name"):
            continue
        yield {
            "uid": m.get("id", m["name"]),
            "name": m["name"].strip(),
            "full_name": (m.get("full_name") or m["name"]).strip(),
            "description": (m.get("description") or "")[:2000],
        }


def iter_tasks(data: list, max_items: int = 0) -> Iterator[dict]:
    """Parse raw tasks JSON into clean dicts."""
    items = data[:max_items] if max_items > 0 else data
    for t in items:
        if not t.get("name"):
            continue
        yield {
            "uid": t.get("id", t["name"]),
            "name": t["name"].strip(),
            "area": (t.get("area") or "").strip(),
            "description": (t.get("description") or "")[:1000],
        }


def iter_datasets(data: list, max_items: int = 0) -> Iterator[dict]:
    """Parse raw datasets JSON into clean dicts."""
    items = data[:max_items] if max_items > 0 else data
    for d in items:
        if not d.get("name"):
            continue
        yield {
            "uid": d.get("id", d["name"]),
            "name": d["name"].strip(),
            "description": (d.get("description") or "")[:1000],
            "modalities": ", ".join(d.get("modalities") or []),
        }
