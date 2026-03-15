"""
Neo4j node models for the GraphRAG knowledge graph.

Each model inherits from BaseNode (uid + created_at) and declares:
- Properties with types and constraints
- Vector indexes for embedding-based similarity search
- Relationships via RelationshipTo / RelationshipFrom
"""

from neomodel import ArrayProperty, BooleanProperty, FloatProperty, IntegerProperty, RelationshipFrom, RelationshipTo, StringProperty

from .base import BaseNode
from .relationships import (
    AddressesTaskRel,
    AuthoredRel,
    CoAuthoredWithRel,
    EvaluatedOnRel,
    HasCodeRel,
    IntroducesMethodRel,
    UsedForRel,
    UsesMethodRel,
)


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
    arxiv_id = StringProperty(index=True)
    url = StringProperty()
    url_pdf = StringProperty()
    date = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Analytics
    community_id = IntegerProperty()

    # Paper <-[:AUTHORED]- Author
    authors = RelationshipFrom("Author", "AUTHORED", model=AuthoredRel)

    # Paper -[:USES_METHOD]-> Method
    methods_used = RelationshipTo("Method", "USES_METHOD", model=UsesMethodRel)

    # Paper -[:INTRODUCES_METHOD]-> Method
    methods_introduced = RelationshipTo("Method", "INTRODUCES_METHOD", model=IntroducesMethodRel)

    # Paper -[:ADDRESSES_TASK]-> Task
    tasks_addressed = RelationshipTo("Task", "ADDRESSES_TASK", model=AddressesTaskRel)

    # Paper -[:HAS_CODE]-> Repository
    repositories = RelationshipTo("Repository", "HAS_CODE", model=HasCodeRel)


class Method(BaseNode):
    """ML method / model node."""

    name = StringProperty(required=True, index=True)
    full_name = StringProperty()
    description = StringProperty()
    category = StringProperty(index=True)
    introduced_year = IntegerProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Analytics
    trend_score = FloatProperty()
    diffusion_path = StringProperty()  # JSON: [{task, year, paper_count}, ...]

    # Method -[:EVALUATED_ON]-> Dataset
    evaluated_on = RelationshipTo("Dataset", "EVALUATED_ON", model=EvaluatedOnRel)

    # Method <-[:USES_METHOD]- Paper
    used_by_papers = RelationshipFrom("Paper", "USES_METHOD", model=UsesMethodRel)

    # Method <-[:INTRODUCES_METHOD]- Paper
    introduced_by_paper = RelationshipFrom("Paper", "INTRODUCES_METHOD", model=IntroducesMethodRel)


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

    # Task <-[:ADDRESSES_TASK]- Paper
    addressed_by_papers = RelationshipFrom("Paper", "ADDRESSES_TASK", model=AddressesTaskRel)


class Dataset(BaseNode):
    """Dataset node."""

    name = StringProperty(required=True, index=True)
    description = StringProperty()
    modalities = StringProperty()
    num_papers = IntegerProperty()
    url = StringProperty()
    embedding = ArrayProperty(base_property=FloatProperty())

    # Dataset -[:USED_FOR]-> Task
    used_for = RelationshipTo("Task", "USED_FOR", model=UsedForRel)
    # Dataset <-[:EVALUATED_ON]- Method
    evaluated_by = RelationshipFrom("Method", "EVALUATED_ON", model=EvaluatedOnRel)


class Repository(BaseNode):
    """Code repository node (e.g., GitHub)."""

    url = StringProperty(required=True, unique_index=True)
    framework = StringProperty()
    stars = IntegerProperty()
    is_official = BooleanProperty(default=False)

    # Repository <-[:HAS_CODE]- Paper
    papers = RelationshipFrom("Paper", "HAS_CODE", model=HasCodeRel)


# Registry of all node models (Author excluded — has no embedding/vector index)
ALL_NODE_MODELS: list[type[BaseNode]] = [Paper, Method, Task, Dataset]

# All models including Author and Repository (for schema installation)
ALL_MODELS: list[type[BaseNode]] = [Author, Paper, Method, Task, Dataset, Repository]
