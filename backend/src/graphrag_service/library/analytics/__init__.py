"""Graph analytics library — community detection, centrality, and trend scoring."""

from .centrality import compute_centrality
from .community import detect_communities
from .trends import compute_trend_scores

__all__ = [
    "detect_communities",
    "compute_centrality",
    "compute_trend_scores",
]
