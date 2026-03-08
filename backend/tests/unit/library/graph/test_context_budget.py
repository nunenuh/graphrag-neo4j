"""Unit tests for library/graph/context_budget.py."""

from graphrag_service.library.graph.context_budget import (
    ContextBudget,
    allocate_context,
    count_tokens,
    truncate_to_budget,
)


class TestContextBudget:
    def test_defaults(self):
        b = ContextBudget()
        assert b.total_tokens == 8000
        assert b.graph_pct == 0.40
        assert b.text_pct == 0.40
        assert b.summary_pct == 0.20

    def test_token_allocation(self):
        b = ContextBudget(total_tokens=10000, graph_pct=0.50, text_pct=0.30, summary_pct=0.20)
        assert b.graph_tokens == 5000
        assert b.text_tokens == 3000
        assert b.summary_tokens == 2000

    def test_immutable(self):
        b = ContextBudget()
        try:
            b.total_tokens = 100  # type: ignore
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestCountTokens:
    def test_empty(self):
        assert count_tokens("") == 0

    def test_short_text(self):
        tokens = count_tokens("Hello world")
        assert tokens > 0
        assert tokens < 10

    def test_longer_text(self):
        tokens = count_tokens("The quick brown fox " * 100)
        assert tokens > 100


class TestTruncateToBudget:
    def test_short_text_unchanged(self):
        text = "Hello"
        result = truncate_to_budget(text, max_tokens=100)
        assert result == "Hello"

    def test_long_text_truncated(self):
        text = "word " * 5000  # ~5000 tokens
        result = truncate_to_budget(text, max_tokens=10)
        assert "[truncated]" in result
        assert len(result) < len(text)

    def test_exact_budget(self):
        text = "Hello world"
        result = truncate_to_budget(text, max_tokens=1000)
        assert result == text


class TestAllocateContext:
    def test_basic(self):
        seeds = [{"label": "Method", "name": "ResNet", "score": 0.95}]
        edges = [{"from_id": "m1", "to_id": "p1", "type": "USES"}]
        result = allocate_context(seeds, edges)
        assert "GRAPH CONTEXT" in result
        assert "ResNet" in result
        assert "USES" in result

    def test_empty(self):
        result = allocate_context([], [])
        assert "GRAPH CONTEXT" in result
        assert "SUMMARY" in result

    def test_custom_budget(self):
        seeds = [{"label": "M", "name": "A", "score": 0.5}]
        budget = ContextBudget(total_tokens=100)
        result = allocate_context(seeds, [], budget)
        tokens = count_tokens(result)
        assert tokens <= 100 + 5  # small tolerance

    def test_many_edges_truncated(self):
        seeds = [{"label": "M", "name": "A", "score": 0.5}]
        edges = [
            {"from_id": f"n{i}", "to_id": f"n{i+1}", "type": "REL"}
            for i in range(1000)
        ]
        budget = ContextBudget(total_tokens=200)
        result = allocate_context(seeds, edges, budget)
        tokens = count_tokens(result)
        assert tokens <= 200 + 5
