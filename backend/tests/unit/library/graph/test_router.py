"""Unit tests for library/graph/router.py."""

from graphrag_service.library.graph.router import (
    DEFAULT_STRATEGY,
    ROUTING_TABLE,
    VALID_QUERY_TYPES,
    VALID_STRATEGIES,
    route_query,
)


class TestRouteQuery:
    def test_factual_lookup(self):
        assert route_query("FACTUAL_LOOKUP") == "GRAPH_ONLY"

    def test_comparison(self):
        assert route_query("COMPARISON") == "HYBRID_PARALLEL"

    def test_temporal(self):
        assert route_query("TEMPORAL") == "GRAPH_ONLY"

    def test_network(self):
        assert route_query("NETWORK") == "HYBRID_PARALLEL"

    def test_exploratory(self):
        assert route_query("EXPLORATORY") == "HYBRID_PARALLEL"

    def test_aggregation(self):
        assert route_query("AGGREGATION") == "GRAPH_ONLY"

    def test_multi_hop(self):
        assert route_query("MULTI_HOP") == "HYBRID_SEQUENTIAL"

    def test_unknown_returns_default(self):
        assert route_query("UNKNOWN_TYPE") == DEFAULT_STRATEGY

    def test_all_types_covered(self):
        assert len(ROUTING_TABLE) == 7

    def test_all_strategies_valid(self):
        for strategy in ROUTING_TABLE.values():
            assert strategy in VALID_STRATEGIES

    def test_all_types_valid(self):
        for qt in ROUTING_TABLE.keys():
            assert qt in VALID_QUERY_TYPES
