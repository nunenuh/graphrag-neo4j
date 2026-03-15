"""Unit tests for library/graph/router.py."""

from graphrag_service.library.graph.router import (
    DEFAULT_STRATEGY,
    DEPTH_TABLE,
    ROUTING_TABLE,
    VALID_QUERY_TYPES,
    VALID_STRATEGIES,
    clamp_depth,
    route_query,
    suggest_depth,
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


class TestSuggestDepth:
    def test_factual_lookup_depth_1(self):
        assert suggest_depth("FACTUAL_LOOKUP") == 1

    def test_multi_hop_depth_3(self):
        assert suggest_depth("MULTI_HOP") == 3

    def test_default_depth_2(self):
        assert suggest_depth("EXPLORATORY") == 2

    def test_unknown_returns_default(self):
        assert suggest_depth("UNKNOWN") == 2

    def test_all_types_have_depth(self):
        for qt in ROUTING_TABLE:
            assert qt in DEPTH_TABLE


class TestClampDepth:
    def test_none_returns_default(self):
        assert clamp_depth(None) == 2

    def test_within_range(self):
        assert clamp_depth(3) == 3

    def test_below_min(self):
        assert clamp_depth(0) == 1

    def test_above_max(self):
        assert clamp_depth(10) == 4

    def test_min_boundary(self):
        assert clamp_depth(1) == 1

    def test_max_boundary(self):
        assert clamp_depth(4) == 4
