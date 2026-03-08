"""Pairwise similarity scoring for entity resolution.

Uses rapidfuzz for fuzzy string matching with a weighted combination
of token_sort_ratio, partial_ratio, and jaro_winkler_similarity.
"""

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from .normalizer import normalize_name

# Scoring weights
_W_TOKEN_SORT = 0.4
_W_PARTIAL = 0.3
_W_JARO_WINKLER = 0.3


def score_pair(name_a: str, name_b: str) -> float:
    """Compute similarity score between two author names.

    Returns a float in [0.0, 1.0] where 1.0 is a perfect match.

    Uses a weighted combination of:
    - token_sort_ratio (0.4): Order-invariant token matching
    - partial_ratio (0.3): Substring matching for initials vs full names
    - jaro_winkler (0.3): Character-level edit distance biased toward prefix
    """
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)

    if not norm_a or not norm_b:
        return 0.0

    if norm_a == norm_b:
        return 1.0

    token_sort = fuzz.token_sort_ratio(norm_a, norm_b) / 100.0
    partial = fuzz.partial_ratio(norm_a, norm_b) / 100.0
    jaro = JaroWinkler.similarity(norm_a, norm_b)

    return (
        _W_TOKEN_SORT * token_sort
        + _W_PARTIAL * partial
        + _W_JARO_WINKLER * jaro
    )
