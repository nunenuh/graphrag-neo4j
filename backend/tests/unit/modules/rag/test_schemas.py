"""Unit tests for RAG module schemas."""

import pytest
from pydantic import ValidationError

from graphrag_service.modules.rag.schemas import (
    EdgeOut,
    QueryRequest,
    QueryResponse,
    SeedNodeOut,
)


class TestQueryRequest:
    def test_valid(self):
        req = QueryRequest(question="What is ResNet?")
        assert req.question == "What is ResNet?"

    def test_empty_question_fails(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="")

    def test_max_length(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="a" * 2001)

    def test_at_max_length(self):
        req = QueryRequest(question="a" * 2000)
        assert len(req.question) == 2000


class TestSeedNodeOut:
    def test_optional_score(self):
        node = SeedNodeOut(id="1", label="Paper", name="P1")
        assert node.score is None

    def test_with_score(self):
        node = SeedNodeOut(id="1", label="Paper", name="P1", score=0.95)
        assert node.score == 0.95


class TestEdgeOut:
    def test_default_properties(self):
        edge = EdgeOut(from_id="a", to_id="b", type="REL")
        assert edge.properties == {}


class TestQueryResponse:
    def test_full(self):
        resp = QueryResponse(
            answer="Answer",
            seed_nodes=[SeedNodeOut(id="1", label="Paper", name="P1", score=0.9)],
            nodes=[{"uid": "1"}],
            edges=[EdgeOut(from_id="a", to_id="b", type="REL")],
            cypher_used="MATCH ...",
            latency_ms=42,
        )
        assert resp.answer == "Answer"
        assert resp.latency_ms == 42
