"""
Neo4j node models for the GraphRAG knowledge graph.

Each model inherits from BaseNode (uid + created_at) and declares:
- Properties with types and constraints
- Vector indexes for embedding-based similarity search
- Relationships via RelationshipTo / RelationshipFrom
"""

from neomodel import ArrayProperty, FloatProperty, RelationshipFrom, RelationshipTo, StringProperty

from .base import BaseNode
from .relationships import EvaluatedOnRel, UsedForRel


class Paper(BaseNode):
    """Research paper node."""

    title = StringProperty(required=True)
    abstract = StringProperty()
    year = StringProperty()
    url = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())


class Method(BaseNode):
    """ML method / model node."""

    name = StringProperty(required=True, index=True)
    full_name = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Method -[:EVALUATED_ON]-> Dataset
    evaluated_on = RelationshipTo("Dataset", "EVALUATED_ON", model=EvaluatedOnRel)


class Task(BaseNode):
    """ML task node (e.g., Image Classification)."""

    name = StringProperty(required=True, index=True)
    area = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Task <-[:USED_FOR]- Dataset
    datasets = RelationshipFrom("Dataset", "USED_FOR", model=UsedForRel)


class Dataset(BaseNode):
    """Dataset node."""

    name = StringProperty(required=True, index=True)
    description = StringProperty()
    modalities = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Dataset -[:USED_FOR]-> Task
    used_for = RelationshipTo("Task", "USED_FOR", model=UsedForRel)
    # Dataset <-[:EVALUATED_ON]- Method
    evaluated_by = RelationshipFrom("Method", "EVALUATED_ON", model=EvaluatedOnRel)


# Registry of all node models
ALL_NODE_MODELS: list[type[BaseNode]] = [Paper, Method, Task, Dataset]
