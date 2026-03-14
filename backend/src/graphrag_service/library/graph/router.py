"""Retrieval strategy routing based on classified query type."""


ROUTING_TABLE: dict[str, str] = {
    "FACTUAL_LOOKUP": "GRAPH_ONLY",
    "COMPARISON": "HYBRID_PARALLEL",
    "TEMPORAL": "GRAPH_ONLY",
    "NETWORK": "HYBRID_PARALLEL",
    "EXPLORATORY": "HYBRID_PARALLEL",
    "AGGREGATION": "GRAPH_ONLY",
    "MULTI_HOP": "HYBRID_SEQUENTIAL",
}

VALID_QUERY_TYPES = set(ROUTING_TABLE.keys())
VALID_STRATEGIES = {"GRAPH_ONLY", "VECTOR_ONLY", "HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"}

DEFAULT_QUERY_TYPE = "EXPLORATORY"
DEFAULT_STRATEGY = "HYBRID_PARALLEL"


def route_query(query_type: str) -> str:
    """Map a classified query type to a retrieval strategy.

    Args:
        query_type: One of 7 query types (e.g. FACTUAL_LOOKUP, COMPARISON).

    Returns:
        Retrieval strategy string (e.g. GRAPH_ONLY, HYBRID_PARALLEL).
    """
    return ROUTING_TABLE.get(query_type, DEFAULT_STRATEGY)
