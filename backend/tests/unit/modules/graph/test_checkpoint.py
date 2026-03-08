"""Unit tests for ingestion checkpoint module."""

import json
from pathlib import Path

import pytest

from graphrag_service.modules.graph.checkpoint import (
    IngestCheckpoint,
    NodeTypeProgress,
    format_checkpoint_report,
    load_checkpoint,
    reset_checkpoint,
    save_checkpoint,
)


class TestNodeTypeProgress:
    def test_initial_state(self):
        p = NodeTypeProgress(label="Paper")
        assert p.total_parsed == 0
        assert p.total_embedded == 0
        assert p.total_upserted == 0
        assert p.skipped_existing == 0
        assert p.last_batch_index == 0
        assert p.completed is False

    def test_mark_batch(self):
        p = NodeTypeProgress(label="Paper")
        p.mark_batch(50, skipped=10)
        assert p.total_parsed == 50
        assert p.total_embedded == 40
        assert p.total_upserted == 50
        assert p.skipped_existing == 10
        assert p.last_batch_index == 1
        assert p.updated_at != ""

    def test_mark_batch_multiple(self):
        p = NodeTypeProgress(label="Method")
        p.mark_batch(50)
        p.mark_batch(30, skipped=5)
        assert p.total_parsed == 80
        assert p.total_embedded == 75
        assert p.total_upserted == 80
        assert p.skipped_existing == 5
        assert p.last_batch_index == 2

    def test_mark_completed(self):
        p = NodeTypeProgress(label="Task")
        p.mark_completed()
        assert p.completed is True
        assert p.updated_at != ""


class TestIngestCheckpoint:
    def test_empty_checkpoint(self):
        c = IngestCheckpoint()
        assert c.node_types == {}
        assert c.started_at != ""
        assert c.is_complete is False

    def test_get_or_create_new(self):
        c = IngestCheckpoint()
        p = c.get_or_create("Paper")
        assert p.label == "Paper"
        assert "Paper" in c.node_types

    def test_get_or_create_existing(self):
        c = IngestCheckpoint()
        p1 = c.get_or_create("Paper")
        p1.mark_batch(10)
        p2 = c.get_or_create("Paper")
        assert p2.total_parsed == 10
        assert p1 is p2

    def test_is_complete_false_when_incomplete(self):
        c = IngestCheckpoint()
        c.get_or_create("Paper")
        assert c.is_complete is False

    def test_is_complete_true_when_all_done(self):
        c = IngestCheckpoint()
        p = c.get_or_create("Paper")
        p.mark_completed()
        assert c.is_complete is True

    def test_is_complete_false_when_mixed(self):
        c = IngestCheckpoint()
        p1 = c.get_or_create("Paper")
        p1.mark_completed()
        c.get_or_create("Method")  # not completed
        assert c.is_complete is False


class TestCheckpointIO:
    def test_load_missing_file(self, tmp_path):
        c = load_checkpoint(tmp_path / "missing.json")
        assert c.node_types == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "progress.json"
        c = IngestCheckpoint()
        p = c.get_or_create("Paper")
        p.mark_batch(100)
        p.mark_completed()
        save_checkpoint(c, path)

        loaded = load_checkpoint(path)
        assert "Paper" in loaded.node_types
        assert loaded.node_types["Paper"].total_parsed == 100
        assert loaded.node_types["Paper"].completed is True

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "progress.json"
        save_checkpoint(IngestCheckpoint(), path)
        assert path.exists()

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        c = load_checkpoint(path)
        assert c.node_types == {}

    def test_load_invalid_schema(self, tmp_path):
        path = tmp_path / "bad_schema.json"
        path.write_text('{"node_types": "not a dict"}', encoding="utf-8")
        c = load_checkpoint(path)
        assert c.node_types == {}

    def test_reset_checkpoint(self, tmp_path):
        path = tmp_path / "progress.json"
        save_checkpoint(IngestCheckpoint(), path)
        assert path.exists()
        reset_checkpoint(path)
        assert not path.exists()

    def test_reset_missing_file_no_error(self, tmp_path):
        reset_checkpoint(tmp_path / "missing.json")  # should not raise

    def test_save_atomic_overwrites(self, tmp_path):
        path = tmp_path / "progress.json"
        c1 = IngestCheckpoint()
        c1.get_or_create("Paper").mark_batch(10)
        save_checkpoint(c1, path)

        c2 = IngestCheckpoint()
        c2.get_or_create("Method").mark_batch(20)
        save_checkpoint(c2, path)

        loaded = load_checkpoint(path)
        assert "Method" in loaded.node_types
        assert loaded.node_types["Method"].total_parsed == 20


class TestFormatCheckpointReport:
    def test_empty_checkpoint(self):
        report = format_checkpoint_report(IngestCheckpoint())
        assert "No progress recorded yet" in report

    def test_with_progress(self):
        c = IngestCheckpoint()
        p = c.get_or_create("Paper")
        p.mark_batch(100, skipped=20)
        p.mark_completed()
        report = format_checkpoint_report(c)
        assert "Paper" in report
        assert "DONE" in report
        assert "100" in report
        assert "20" in report

    def test_in_progress(self):
        c = IngestCheckpoint()
        c.get_or_create("Method").mark_batch(50)
        report = format_checkpoint_report(c)
        assert "IN PROGRESS" in report
