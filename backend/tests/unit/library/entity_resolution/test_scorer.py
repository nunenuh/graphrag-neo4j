"""Unit tests for library/entity_resolution/scorer.py."""

import pytest

from graphrag_service.library.entity_resolution.scorer import score_pair


class TestScorePair:
    def test_identical(self):
        assert score_pair("Geoffrey Hinton", "Geoffrey Hinton") == 1.0

    def test_identical_case_insensitive(self):
        assert score_pair("geoffrey hinton", "Geoffrey Hinton") == 1.0

    def test_high_similarity_initial_vs_full(self):
        # G. Hinton vs Geoffrey Hinton — should be reasonably high
        score = score_pair("G. Hinton", "Geoffrey Hinton")
        assert score > 0.5  # Partial match should catch this

    def test_high_similarity_diacritics(self):
        score = score_pair("Sören Müller", "Soren Muller")
        assert score == 1.0  # After normalization, identical

    def test_low_similarity_different_people(self):
        score = score_pair("Geoffrey Hinton", "Yann LeCun")
        assert score < 0.5

    def test_empty_name(self):
        assert score_pair("", "Geoffrey Hinton") == 0.0
        assert score_pair("Geoffrey Hinton", "") == 0.0

    def test_both_empty(self):
        assert score_pair("", "") == 0.0

    def test_suffix_stripping(self):
        score = score_pair("Billie F. Spencer Jr", "Billie F. Spencer")
        assert score == 1.0  # After normalization, identical

    def test_returns_float_in_range(self):
        score = score_pair("John Smith", "Jane Doe")
        assert 0.0 <= score <= 1.0
