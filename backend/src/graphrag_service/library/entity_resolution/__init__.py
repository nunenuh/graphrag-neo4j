"""Entity resolution library — name normalization, scoring, and blocking."""

from .blocker import build_blocks, find_clusters
from .merger import MergedAuthor, deterministic_uid, merge_clusters
from .normalizer import compute_blocking_key, normalize_name, parse_name_parts
from .scorer import score_pair

__all__ = [
    "normalize_name",
    "compute_blocking_key",
    "parse_name_parts",
    "score_pair",
    "build_blocks",
    "find_clusters",
    "merge_clusters",
    "MergedAuthor",
    "deterministic_uid",
]
