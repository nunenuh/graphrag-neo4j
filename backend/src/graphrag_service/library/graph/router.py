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

# Suggested traversal depth per query type
DEPTH_TABLE: dict[str, int] = {
    "FACTUAL_LOOKUP": 1,
    "COMPARISON": 2,
    "TEMPORAL": 2,
    "NETWORK": 2,
    "EXPLORATORY": 2,
    "AGGREGATION": 2,
    "MULTI_HOP": 3,
}

DEFAULT_DEPTH = 2
MIN_DEPTH = 1
MAX_DEPTH = 4


def route_query(query_type: str) -> str:
    """Map a classified query type to a retrieval strategy.

    Args:
        query_type: One of 7 query types (e.g. FACTUAL_LOOKUP, COMPARISON).

    Returns:
        Retrieval strategy string (e.g. GRAPH_ONLY, HYBRID_PARALLEL).
    """
    return ROUTING_TABLE.get(query_type, DEFAULT_STRATEGY)


def suggest_depth(query_type: str) -> int:
    """Suggest traversal depth for a query type.

    Args:
        query_type: Classified query type.

    Returns:
        Suggested hop depth (1-4).
    """
    return DEPTH_TABLE.get(query_type, DEFAULT_DEPTH)


def clamp_depth(depth: int | None) -> int:
    """Clamp depth to valid range [MIN_DEPTH, MAX_DEPTH].

    If None, returns DEFAULT_DEPTH.
    """
    if depth is None:
        return DEFAULT_DEPTH
    return max(MIN_DEPTH, min(MAX_DEPTH, depth))
