"""Unit tests for library.parsers."""

import pytest

from graphrag_service.library.parsers import (
    iter_author_paper_edges,
    iter_authors,
    iter_datasets,
    iter_methods,
    iter_papers,
    iter_tasks,
)


class TestIterPapers:
    def test_basic(self):
        data = [
            {"title": "Paper A", "abstract": "Abstract A", "paper_url": "http://a", "published": "2024-01-01"},
        ]
        results = list(iter_papers(data))
        assert len(results) == 1
        assert results[0]["uid"] == "http://a"
        assert results[0]["title"] == "Paper A"
        assert results[0]["year"] == "2024"

    def test_skips_missing_title(self):
        data = [{"abstract": "A"}]
        assert list(iter_papers(data)) == []

    def test_skips_missing_abstract(self):
        data = [{"title": "T"}]
        assert list(iter_papers(data)) == []

    def test_max_papers(self):
        data = [{"title": f"P{i}", "abstract": f"A{i}"} for i in range(10)]
        results = list(iter_papers(data, max_papers=3))
        assert len(results) == 3

    def test_truncates_abstract(self):
        data = [{"title": "T", "abstract": "x" * 3000, "paper_url": "u"}]
        results = list(iter_papers(data))
        assert len(results[0]["abstract"]) == 2000

    def test_strips_whitespace(self):
        data = [{"title": "  Paper A  ", "abstract": " Abstract ", "paper_url": "u"}]
        results = list(iter_papers(data))
        assert results[0]["title"] == "Paper A"
        assert results[0]["abstract"] == "Abstract"


class TestIterMethods:
    def test_basic(self):
        data = [{"name": "ResNet", "id": "m1", "description": "A method"}]
        results = list(iter_methods(data))
        assert len(results) == 1
        assert results[0]["uid"] == "m1"
        assert results[0]["name"] == "ResNet"

    def test_skips_missing_name(self):
        data = [{"description": "no name"}]
        assert list(iter_methods(data)) == []

    def test_max_items(self):
        data = [{"name": f"M{i}"} for i in range(10)]
        results = list(iter_methods(data, max_items=3))
        assert len(results) == 3

    def test_max_items_zero_means_all(self):
        data = [{"name": f"M{i}"} for i in range(5)]
        results = list(iter_methods(data, max_items=0))
        assert len(results) == 5

    def test_fallback_uid_to_name(self):
        data = [{"name": "Test"}]
        results = list(iter_methods(data))
        assert results[0]["uid"] == "Test"


class TestIterTasks:
    def test_basic(self):
        data = [{"name": "Image Classification", "id": "t1", "area": "CV"}]
        results = list(iter_tasks(data))
        assert results[0]["area"] == "CV"

    def test_skips_missing_name(self):
        assert list(iter_tasks([{"area": "CV"}])) == []

    def test_truncates_description(self):
        data = [{"name": "T", "description": "x" * 2000}]
        results = list(iter_tasks(data))
        assert len(results[0]["description"]) == 1000


class TestIterDatasets:
    def test_basic(self):
        data = [{"name": "CIFAR-10", "id": "d1", "modalities": ["image", "label"]}]
        results = list(iter_datasets(data))
        assert results[0]["modalities"] == "image, label"

    def test_skips_missing_name(self):
        assert list(iter_datasets([{"modalities": ["text"]}])) == []

    def test_empty_modalities(self):
        data = [{"name": "D1"}]
        results = list(iter_datasets(data))
        assert results[0]["modalities"] == ""


class TestIterAuthors:
    def test_extracts_unique_authors(self):
        data = [
            {"title": "P1", "abstract": "A1", "authors": ["Alice", "Bob"]},
            {"title": "P2", "abstract": "A2", "authors": ["Bob", "Carol"]},
        ]
        results = list(iter_authors(data))
        names = [r["name"] for r in results]
        assert names == ["Alice", "Bob", "Carol"]

    def test_uid_format(self):
        data = [{"authors": ["Geoffrey Hinton"]}]
        results = list(iter_authors(data))
        assert results[0]["uid"] == "author:geoffrey_hinton"

    def test_skips_empty_names(self):
        data = [{"authors": ["", "  ", "Alice"]}]
        results = list(iter_authors(data))
        assert len(results) == 1
        assert results[0]["name"] == "Alice"

    def test_no_authors_key(self):
        data = [{"title": "P1"}]
        assert list(iter_authors(data)) == []

    def test_max_papers(self):
        data = [
            {"authors": ["Alice"]},
            {"authors": ["Bob"]},
            {"authors": ["Carol"]},
        ]
        results = list(iter_authors(data, max_papers=2))
        names = [r["name"] for r in results]
        assert "Carol" not in names

    def test_strips_whitespace(self):
        data = [{"authors": ["  Alice  "]}]
        results = list(iter_authors(data))
        assert results[0]["name"] == "Alice"


class TestIterAuthorPaperEdges:
    def test_basic(self):
        data = [
            {"title": "P1", "abstract": "A1", "paper_url": "http://p1", "authors": ["Alice", "Bob"]},
        ]
        edges = list(iter_author_paper_edges(data))
        assert len(edges) == 2
        assert edges[0]["author_name"] == "Alice"
        assert edges[0]["paper_uid"] == "http://p1"
        assert edges[0]["order"] == 0
        assert edges[1]["order"] == 1

    def test_skips_papers_without_title(self):
        data = [{"abstract": "A1", "authors": ["Alice"]}]
        assert list(iter_author_paper_edges(data)) == []

    def test_skips_empty_author_names(self):
        data = [{"title": "P1", "abstract": "A1", "paper_url": "u", "authors": ["", "Alice"]}]
        edges = list(iter_author_paper_edges(data))
        assert len(edges) == 1
        assert edges[0]["author_name"] == "Alice"

    def test_max_papers(self):
        data = [
            {"title": "P1", "abstract": "A1", "paper_url": "u1", "authors": ["Alice"]},
            {"title": "P2", "abstract": "A2", "paper_url": "u2", "authors": ["Bob"]},
        ]
        edges = list(iter_author_paper_edges(data, max_papers=1))
        assert len(edges) == 1
        assert edges[0]["author_name"] == "Alice"
