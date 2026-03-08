"""Tests for evaluation queries module."""

from tests.evaluation.queries import (
    CATEGORIES,
    AGGREGATION_QUERIES,
    COMPARISON_QUERIES,
    EXPLORATORY_QUERIES,
    FACTUAL_QUERIES,
    MULTI_HOP_QUERIES,
    NETWORK_QUERIES,
    TEMPORAL_QUERIES,
    EvalQuery,
    get_all_queries,
    get_queries_by_category,
)


class TestEvalQuery:
    """Test EvalQuery dataclass."""

    def test_eval_query_is_frozen(self):
        q = EvalQuery(id="t1", category="TEST", question="test?")
        try:
            q.id = "changed"
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_eval_query_defaults(self):
        q = EvalQuery(id="t1", category="TEST", question="test?")
        assert q.expected_entities == []
        assert q.expected_relationships == []
        assert q.min_hops == 1
        assert q.gold_answer_keywords == []
        assert q.difficulty == "medium"


class TestGetAllQueries:
    """Test get_all_queries function."""

    def test_returns_40_queries(self):
        queries = get_all_queries()
        assert len(queries) == 40

    def test_all_have_unique_ids(self):
        queries = get_all_queries()
        ids = [q.id for q in queries]
        assert len(ids) == len(set(ids))

    def test_all_have_required_fields(self):
        for q in get_all_queries():
            assert q.id
            assert q.category
            assert q.question

    def test_all_categories_represented(self):
        queries = get_all_queries()
        categories = {q.category for q in queries}
        assert categories == set(CATEGORIES)

    def test_category_counts(self):
        queries = get_all_queries()
        counts = {}
        for q in queries:
            counts[q.category] = counts.get(q.category, 0) + 1
        assert counts["FACTUAL_LOOKUP"] == 6
        assert counts["COMPARISON"] == 6
        assert counts["TEMPORAL"] == 6
        assert counts["NETWORK"] == 5
        assert counts["EXPLORATORY"] == 7
        assert counts["AGGREGATION"] == 5
        assert counts["MULTI_HOP"] == 5


class TestGetQueriesByCategory:
    """Test get_queries_by_category function."""

    def test_returns_correct_category(self):
        queries = get_queries_by_category("FACTUAL_LOOKUP")
        assert len(queries) == 6
        assert all(q.category == "FACTUAL_LOOKUP" for q in queries)

    def test_invalid_category_returns_empty(self):
        queries = get_queries_by_category("NONEXISTENT")
        assert queries == []

    def test_each_category_returns_queries(self):
        for cat in CATEGORIES:
            queries = get_queries_by_category(cat)
            assert len(queries) > 0, f"No queries for {cat}"
