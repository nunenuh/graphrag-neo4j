"""Unit tests for graph module schemas."""

from graphrag_service.modules.graph.schemas import (
    GraphEdgeOut,
    GraphExploreResponse,
    GraphSchemaResponse,
    GraphStatsResponse,
    NodeDetailResponse,
    NodeSearchResponse,
    NodeSearchResultOut,
)


class TestGraphSchemas:
    def test_schema_response(self):
        resp = GraphSchemaResponse(node_labels=["Paper"], relationship_types=["USED_FOR"])
        assert resp.node_labels == ["Paper"]

    def test_explore_response(self):
        resp = GraphExploreResponse(
            nodes=[{"id": "1"}],
            edges=[GraphEdgeOut(from_id="a", to_id="b", type="REL")],
        )
        assert len(resp.nodes) == 1
        assert resp.edges[0].type == "REL"

    def test_stats_response(self):
        resp = GraphStatsResponse(
            total_nodes=100, total_edges=50,
            node_counts={"Paper": 50}, edge_counts={"USED_FOR": 50},
        )
        assert resp.total_nodes == 100

    def test_node_detail_response(self):
        resp = NodeDetailResponse(uid="p1", label="Paper")
        assert resp.uid == "p1"
        assert resp.properties == {}
        assert resp.outgoing == []

    def test_node_search_response(self):
        result = NodeSearchResultOut(uid="m1", label="Method", name="ResNet")
        resp = NodeSearchResponse(results=[result], count=1)
        assert resp.count == 1
        assert resp.results[0].name == "ResNet"
