"""Unit tests for BM25 fulltext search module."""

import pytest

from graphrag_service.library.graph.bm25_search import (
    FULLTEXT_INDEXES,
    _escape_lucene,
    bm25_search,
    create_fulltext_indexes,
)


# ── _escape_lucene ──────────────────────────────────────────────


class TestEscapeLucene:
    def test_plain_text_unchanged(self):
        assert _escape_lucene("hello world") == "hello world"

    def test_special_chars_escaped(self):
        result = _escape_lucene("query+type:test")
        assert result == "query\\+type\\:test"

    def test_all_special_chars(self):
        for ch in r'+-&|!(){}[]^"~*?:\/':
            result = _escape_lucene(ch)
            assert result == f"\\{ch}", f"Failed to escape '{ch}'"

    def test_empty_string(self):
        assert _escape_lucene("") == ""

    def test_mixed_content(self):
        result = _escape_lucene("(neural network) AND attention")
        assert result == "\\(neural network\\) AND attention"


# ── create_fulltext_indexes ─────────────────────────────────────


class TestCreateFulltextIndexes:
    def test_creates_all_indexes(self):
        calls = []

        def mock_run(cypher, params=None):
            calls.append(cypher)

        count = create_fulltext_indexes(mock_run)
        assert count == len(FULLTEXT_INDEXES)
        assert len(calls) == len(FULLTEXT_INDEXES)

    def test_cypher_contains_index_name(self):
        calls = []

        def mock_run(cypher, params=None):
            calls.append(cypher)

        create_fulltext_indexes(mock_run)
        for call, (index_name, label, _) in zip(calls, FULLTEXT_INDEXES):
            assert index_name in call
            assert label in call

    def test_handles_create_error(self):
        def mock_run(cypher, params=None):
            raise RuntimeError("index exists")

        count = create_fulltext_indexes(mock_run)
        assert count == 0


# ── bm25_search ─────────────────────────────────────────────────


class TestBm25Search:
    def test_empty_query_returns_empty(self):
        result = bm25_search("", lambda *a, **kw: [], top_k=5)
        assert result == []

    def test_whitespace_query_returns_empty(self):
        result = bm25_search("   ", lambda *a, **kw: [], top_k=5)
        assert result == []

    def test_returns_sorted_by_score(self):
        fake_rows = [
            {"node": {"uid": "a", "name": "Paper A"}, "score": 1.5, "label": "Paper"},
            {"node": {"uid": "b", "name": "Paper B"}, "score": 3.0, "label": "Paper"},
            {"node": {"uid": "c", "name": "Paper C"}, "score": 2.0, "label": "Paper"},
        ]
        call_count = [0]

        def mock_run(cypher, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return fake_rows
            return []

        results = bm25_search("test query", mock_run, top_k=10)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_limit(self):
        fake_rows = [
            {"node": {"uid": f"n{i}", "name": f"Node {i}"}, "score": float(i), "label": "Paper"}
            for i in range(10)
        ]

        def mock_run(cypher, params=None):
            return fake_rows

        results = bm25_search("test", mock_run, top_k=3)
        assert len(results) <= 3

    def test_excludes_embedding_from_properties(self):
        fake_rows = [
            {
                "node": {"uid": "x", "name": "Test", "embedding": [0.1, 0.2]},
                "score": 1.0,
                "label": "Method",
            },
        ]

        def mock_run(cypher, params=None):
            if "fulltext_method" in params.get("index", ""):
                return fake_rows
            return []

        results = bm25_search("test", mock_run, top_k=5)
        for r in results:
            assert "embedding" not in r["properties"]

    def test_handles_index_failure_gracefully(self):
        call_count = [0]

        def mock_run(cypher, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("index missing")
            return []

        # Should not raise, just skip failed index
        results = bm25_search("test", mock_run, top_k=5)
        assert isinstance(results, list)

    def test_result_structure(self):
        fake_rows = [
            {
                "node": {"uid": "u1", "title": "My Paper", "abstract": "stuff"},
                "score": 2.5,
                "label": "Paper",
            },
        ]

        def mock_run(cypher, params=None):
            if "fulltext_paper" in params.get("index", ""):
                return fake_rows
            return []

        results = bm25_search("test", mock_run, top_k=5)
        assert len(results) >= 1
        r = results[0]
        assert r["uid"] == "u1"
        assert r["label"] == "Paper"
        assert r["name"] == "My Paper"  # falls back to title
        assert r["score"] == 2.5
        assert "properties" in r
