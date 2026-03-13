"""
Neo4j relationship models for the GraphRAG knowledge graph.

Uses neomodel StructuredRel for typed relationship properties.
"""

from neomodel import IntegerProperty, StringProperty, StructuredRel


class UsedForRel(StructuredRel):
    """Dataset -[:USED_FOR]-> Task relationship."""

    pass


class EvaluatedOnRel(StructuredRel):
    """Method -[:EVALUATED_ON]-> Dataset relationship with metric properties."""

    metric = StringProperty()
    score = StringProperty()


class AuthoredRel(StructuredRel):
    """Author -[:AUTHORED]-> Paper relationship.

    Properties:
        order: Author position in the paper's author list (0-based).
    """

    order = IntegerProperty()


class CoAuthoredWithRel(StructuredRel):
    """Author -[:CO_AUTHORED_WITH]-> Author. Derived from shared papers."""

    paper_count = IntegerProperty(default=0)
