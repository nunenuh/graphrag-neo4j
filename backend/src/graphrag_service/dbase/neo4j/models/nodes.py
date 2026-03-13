"""
Neo4j node models for the GraphRAG knowledge graph.

Each model inherits from BaseNode (uid + created_at) and declares:
- Properties with types and constraints
- Vector indexes for embedding-based similarity search
- Relationships via RelationshipTo / RelationshipFrom
"""

from neomodel import ArrayProperty, FloatProperty, IntegerProperty, RelationshipFrom, RelationshipTo, StringProperty

from .base import BaseNode
from .relationships import AuthoredRel, CoAuthoredWithRel, EvaluatedOnRel, UsedForRel


class Author(BaseNode):
    """Author node for entity resolution.

    Properties:
        name: Original raw name from PwC data.
        name_normalized: Lowercased, diacritics-stripped, suffix-removed name.
        blocking_key: last_name + first_initial for candidate grouping.
        aliases: JSON-encoded list of alternative name strings.
        merged_into: uid of the canonical author (set after ER merge).
    """

    name = StringProperty(required=True, index=True)
    name_normalized = StringProperty(index=True)
    blocking_key = StringProperty(index=True)
    aliases = StringProperty(default="[]")
    merged_into = StringProperty()

    # Analytics (computed by graph analytics pipeline)
    community_id = IntegerProperty()
    pagerank = FloatProperty()
    betweenness = FloatProperty()
    h_index = IntegerProperty()

    # Author -[:AUTHORED]-> Paper
    papers = RelationshipTo("Paper", "AUTHORED", model=AuthoredRel)

    # Author -[:CO_AUTHORED_WITH]-> Author
    co_authors = RelationshipTo("Author", "CO_AUTHORED_WITH", model=CoAuthoredWithRel)


class Paper(BaseNode):
    """Research paper node."""

    title = StringProperty(required=True)
    abstract = StringProperty()
    year = StringProperty()
    url = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Analytics
    community_id = IntegerProperty()

    # Paper <-[:AUTHORED]- Author
    authors = RelationshipFrom("Author", "AUTHORED", model=AuthoredRel)


class Method(BaseNode):
    """ML method / model node."""

    name = StringProperty(required=True, index=True)
    full_name = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Analytics
    trend_score = FloatProperty()
    diffusion_path = StringProperty()  # JSON: [{task, year, paper_count}, ...]

    # Method -[:EVALUATED_ON]-> Dataset
    evaluated_on = RelationshipTo("Dataset", "EVALUATED_ON", model=EvaluatedOnRel)


class Task(BaseNode):
    """ML task node (e.g., Image Classification)."""

    name = StringProperty(required=True, index=True)
    area = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Analytics
    trend_score = FloatProperty()

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


# Registry of all node models (Author excluded — has no embedding/vector index)
ALL_NODE_MODELS: list[type[BaseNode]] = [Paper, Method, Task, Dataset]

# All models including Author (for schema installation)
ALL_MODELS: list[type[BaseNode]] = [Author, Paper, Method, Task, Dataset]
