"""Unit tests for library/entity_resolution/normalizer.py."""

import pytest

from graphrag_service.library.entity_resolution.normalizer import (
    NameParts,
    compute_blocking_key,
    normalize_name,
    parse_name_parts,
)


class TestNormalizeName:
    def test_basic(self):
        assert normalize_name("Geoffrey Hinton") == "geoffrey hinton"

    def test_diacritics(self):
        assert normalize_name("Sören Müller") == "soren muller"

    def test_suffix_jr(self):
        assert normalize_name("Billie F. Spencer Jr") == "billie f. spencer"

    def test_suffix_phd(self):
        assert normalize_name("Jane Doe Ph.D.") == "jane doe"

    def test_suffix_iii(self):
        assert normalize_name("John Smith III") == "john smith"

    def test_whitespace_collapse(self):
        assert normalize_name("  John   Smith  ") == "john smith"

    def test_empty(self):
        assert normalize_name("") == ""

    def test_none_like(self):
        assert normalize_name("") == ""

    def test_unicode_nfd(self):
        # é decomposed is e + combining accent
        assert normalize_name("José García") == "jose garcia"


class TestParseNameParts:
    def test_first_last(self):
        parts = parse_name_parts("Geoffrey Hinton")
        assert parts == NameParts(first="geoffrey", last="hinton", first_initial="g")

    def test_first_middle_last(self):
        parts = parse_name_parts("Billie F. Spencer")
        assert parts.first == "billie"
        assert parts.last == "spencer"
        assert parts.first_initial == "b"

    def test_last_comma_first(self):
        parts = parse_name_parts("Hinton, Geoffrey")
        assert parts.first == "geoffrey"
        assert parts.last == "hinton"
        assert parts.first_initial == "g"

    def test_single_name(self):
        parts = parse_name_parts("Madonna")
        assert parts.first == ""
        assert parts.last == "madonna"
        assert parts.first_initial == ""

    def test_empty(self):
        parts = parse_name_parts("")
        assert parts == NameParts(first="", last="", first_initial="")


class TestComputeBlockingKey:
    def test_normal(self):
        assert compute_blocking_key("Geoffrey Hinton") == "hinton_g"

    def test_diacritics(self):
        assert compute_blocking_key("Sören Hinton") == "hinton_s"

    def test_single_name(self):
        assert compute_blocking_key("Madonna") == "madonna"

    def test_empty(self):
        assert compute_blocking_key("") == ""

    def test_matching_variants(self):
        # G. Hinton and Geoffrey Hinton should have the same blocking key
        key1 = compute_blocking_key("G. Hinton")
        key2 = compute_blocking_key("Geoffrey Hinton")
        assert key1 == key2 == "hinton_g"
