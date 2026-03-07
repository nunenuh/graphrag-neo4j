"""
Neo4j relationship models for the GraphRAG knowledge graph.

Uses neomodel StructuredRel for typed relationship properties.
"""

from neomodel import StringProperty, StructuredRel


class UsedForRel(StructuredRel):
    """Dataset -[:USED_FOR]-> Task relationship."""

    pass


class EvaluatedOnRel(StructuredRel):
    """Method -[:EVALUATED_ON]-> Dataset relationship with metric properties."""

    metric = StringProperty()
    score = StringProperty()
