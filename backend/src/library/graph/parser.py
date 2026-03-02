import json
from pathlib import Path
from typing import Iterator

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
# parser.py lives at: backend/src/library/graph/parser.py
# .parent×5 walks up to repo root, then /data → graphrag-neo4j/data/
MAX_PAPERS = 5000


def _load(filename: str) -> list:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def iter_papers() -> Iterator[dict]:
    for p in _load("papers.json")[:MAX_PAPERS]:
        if not p.get("title") or not p.get("abstract"):
            continue
        yield {
            "id":       p.get("paper_url", p.get("id", "")),
            "title":    p["title"].strip(),
            "abstract": p["abstract"].strip()[:2000],
            "year":     p.get("published", "")[:4],
            "url":      p.get("paper_url", ""),
        }


def iter_methods() -> Iterator[dict]:
    for m in _load("methods.json"):
        if not m.get("name"):
            continue
        yield {
            "id":          m.get("id", m["name"]),
            "name":        m["name"].strip(),
            "full_name":   m.get("full_name", m["name"]).strip(),
            "description": (m.get("description") or "")[:2000],
        }


def iter_tasks() -> Iterator[dict]:
    for t in _load("tasks.json"):
        if not t.get("name"):
            continue
        yield {
            "id":          t.get("id", t["name"]),
            "name":        t["name"].strip(),
            "area":        t.get("area", "").strip(),
            "description": (t.get("description") or "")[:1000],
        }


def iter_datasets() -> Iterator[dict]:
    for d in _load("datasets.json"):
        if not d.get("name"):
            continue
        yield {
            "id":          d.get("id", d["name"]),
            "name":        d["name"].strip(),
            "description": (d.get("description") or "")[:1000],
            "modalities":  ", ".join(d.get("modalities", [])),
        }
