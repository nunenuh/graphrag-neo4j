"""
Neo4j model base — abstract base node and re-exports from neomodel.
"""

from neomodel import (
    ArrayProperty,
    DateTimeProperty,
    FloatProperty,
    IntegerProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    StructuredRel,
    UniqueIdProperty,
)
from neomodel.properties import VectorIndex


class BaseNode(StructuredNode):
    """Abstract base for all graph nodes.

    Provides a uid (natural business key) and a created_at timestamp.
    Concrete subclasses must NOT set __abstract_node__ — only this base does.
    """

    __abstract_node__ = True

    uid = StringProperty(unique_index=True, required=True)
    created_at = DateTimeProperty(default_now=True)


__all__ = [
    "BaseNode",
    "StructuredNode",
    "StructuredRel",
    "StringProperty",
    "IntegerProperty",
    "FloatProperty",
    "ArrayProperty",
    "DateTimeProperty",
    "UniqueIdProperty",
    "RelationshipTo",
    "RelationshipFrom",
    "VectorIndex",
]
