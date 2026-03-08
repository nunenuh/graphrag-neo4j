"""
Ingestion progress checkpoint — tracks last successful batch per node type.

Allows resuming ingestion after interruption without re-processing everything.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class NodeTypeProgress(BaseModel):
    """Progress state for a single node type."""

    label: str
    total_parsed: int = 0
    total_embedded: int = 0
    total_upserted: int = 0
    skipped_existing: int = 0
    last_batch_index: int = 0
    completed: bool = False
    updated_at: str = ""

    def mark_batch(self, batch_size: int, skipped: int = 0) -> None:
        """Record a completed batch."""
        self.total_parsed += batch_size
        self.total_embedded += batch_size - skipped
        self.total_upserted += batch_size
        self.skipped_existing += skipped
        self.last_batch_index += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self) -> None:
        """Mark this node type as fully ingested."""
        self.completed = True
        self.updated_at = datetime.now(timezone.utc).isoformat()


class IngestCheckpoint(BaseModel):
    """Full ingestion checkpoint state."""

    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = ""
    node_types: dict[str, NodeTypeProgress] = Field(default_factory=dict)

    def get_or_create(self, label: str) -> NodeTypeProgress:
        """Get progress for a node type, creating if needed."""
        if label not in self.node_types:
            self.node_types[label] = NodeTypeProgress(label=label)
        return self.node_types[label]

    @property
    def is_complete(self) -> bool:
        """True if all tracked node types are completed."""
        return bool(self.node_types) and all(
            nt.completed for nt in self.node_types.values()
        )


DEFAULT_CHECKPOINT_PATH = Path("data/.ingest_progress.json")


def load_checkpoint(path: Optional[Path] = None) -> IngestCheckpoint:
    """Load checkpoint from disk. Returns empty checkpoint if file missing."""
    p = path or DEFAULT_CHECKPOINT_PATH
    if not p.exists():
        return IngestCheckpoint()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return IngestCheckpoint.model_validate(raw)
    except (json.JSONDecodeError, ValueError):
        return IngestCheckpoint()


def save_checkpoint(checkpoint: IngestCheckpoint, path: Optional[Path] = None) -> None:
    """Atomically save checkpoint to disk."""
    p = path or DEFAULT_CHECKPOINT_PATH
    checkpoint.updated_at = datetime.now(timezone.utc).isoformat()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(checkpoint.model_dump_json(indent=2), encoding="utf-8")
    tmp.rename(p)


def reset_checkpoint(path: Optional[Path] = None) -> None:
    """Delete checkpoint file to start fresh."""
    p = path or DEFAULT_CHECKPOINT_PATH
    if p.exists():
        p.unlink()


def format_checkpoint_report(checkpoint: IngestCheckpoint) -> str:
    """Format checkpoint as a human-readable report string."""
    lines = [
        f"Ingestion Progress (started: {checkpoint.started_at})",
        f"Last updated: {checkpoint.updated_at or 'never'}",
        "",
    ]
    if not checkpoint.node_types:
        lines.append("  No progress recorded yet.")
        return "\n".join(lines)

    for label, progress in checkpoint.node_types.items():
        status = "DONE" if progress.completed else "IN PROGRESS"
        lines.append(f"  {label}: [{status}]")
        lines.append(f"    Parsed:   {progress.total_parsed}")
        lines.append(f"    Embedded: {progress.total_embedded}")
        lines.append(f"    Upserted: {progress.total_upserted}")
        lines.append(f"    Skipped (already embedded): {progress.skipped_existing}")
        lines.append(f"    Batches completed: {progress.last_batch_index}")
        lines.append("")

    return "\n".join(lines)
