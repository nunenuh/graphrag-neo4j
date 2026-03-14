"""Unit tests for Neo4j relationship models."""

import pytest
from neomodel import IntegerProperty, StructuredRel


class TestCoAuthoredWithRel:
    """Tests for the CoAuthoredWithRel relationship model."""

    def test_import(self):
        """CoAuthoredWithRel can be imported from models package."""
        from graphrag_service.dbase.neo4j.models import CoAuthoredWithRel

        assert CoAuthoredWithRel is not None

    def test_is_structured_rel(self):
        """CoAuthoredWithRel inherits from StructuredRel."""
        from graphrag_service.dbase.neo4j.models.relationships import CoAuthoredWithRel

        assert issubclass(CoAuthoredWithRel, StructuredRel)

    def test_has_paper_count_property(self):
        """CoAuthoredWithRel has a paper_count IntegerProperty with default 0."""
        from graphrag_service.dbase.neo4j.models.relationships import CoAuthoredWithRel

        prop = CoAuthoredWithRel.defined_properties()["paper_count"]
        assert isinstance(prop, IntegerProperty)
        assert prop.default == 0

    def test_author_has_co_authors_relationship(self):
        """Author node has a co_authors relationship using CoAuthoredWithRel."""
        from graphrag_service.dbase.neo4j.models.nodes import Author

        rel_manager = Author.co_authors
        assert rel_manager.definition["relation_type"] == "CO_AUTHORED_WITH"
