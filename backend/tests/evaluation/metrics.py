"""Quality metrics computation for evaluation framework."""

from dataclasses import dataclass, field
import statistics


@dataclass
class EvalResult:
    """Result of evaluating a single query."""

    query_id: str
    category: str
    question: str
    answer: str
    seed_nodes: list[dict] = field(default_factory=list)
    subgraph: dict = field(default_factory=dict)
    latency_ms: int = 0
    query_type: str = ""
    retrieval_strategy: str = ""
    provenance_score: float = 0.0
    unsupported_claims: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


def entity_extraction_f1(
    expected_entities: list[str],
    retrieved_entities: list[str],
) -> float:
    """Compute F1 score for entity extraction.

    Args:
        expected_entities: Gold standard entity names.
        retrieved_entities: Entities found in retrieved subgraph.

    Returns:
        F1 score (0.0 to 1.0).
    """
    if not expected_entities:
        return 1.0 if not retrieved_entities else 0.0

    expected_lower = {e.lower() for e in expected_entities}
    retrieved_lower = {e.lower() for e in retrieved_entities}

    true_positives = len(expected_lower & retrieved_lower)

    if true_positives == 0:
        return 0.0

    precision = true_positives / len(retrieved_lower) if retrieved_lower else 0.0
    recall = true_positives / len(expected_lower) if expected_lower else 0.0

    if precision + recall == 0:
        return 0.0

    return round(2 * precision * recall / (precision + recall), 4)


def retrieval_precision_at_k(
    expected_entities: list[str],
    seed_nodes: list[dict],
    k: int = 10,
) -> float:
    """Compute precision@k for retrieval.

    Args:
        expected_entities: Gold standard entity names.
        seed_nodes: Retrieved seed nodes (with 'name' key).
        k: Number of top results to consider.

    Returns:
        Precision@k (0.0 to 1.0).
    """
    if not expected_entities:
        return 1.0

    top_k = seed_nodes[:k]
    if not top_k:
        return 0.0

    expected_lower = {e.lower() for e in expected_entities}
    relevant = sum(
        1 for node in top_k
        if any(exp in node.get("name", "").lower() for exp in expected_lower)
    )
    return round(relevant / len(top_k), 4)


def retrieval_recall_at_k(
    expected_entities: list[str],
    seed_nodes: list[dict],
    k: int = 10,
) -> float:
    """Compute recall@k for retrieval.

    Args:
        expected_entities: Gold standard entity names.
        seed_nodes: Retrieved seed nodes (with 'name' key).
        k: Number of top results to consider.

    Returns:
        Recall@k (0.0 to 1.0).
    """
    if not expected_entities:
        return 1.0

    top_k = seed_nodes[:k]
    if not top_k:
        return 0.0

    expected_lower = {e.lower() for e in expected_entities}
    retrieved_names = {node.get("name", "").lower() for node in top_k}

    found = sum(
        1 for exp in expected_lower
        if any(exp in name for name in retrieved_names)
    )
    return round(found / len(expected_lower), 4)


def keyword_coverage(
    gold_keywords: list[str],
    answer: str,
) -> float:
    """Compute fraction of gold keywords present in the answer.

    Args:
        gold_keywords: Expected keywords in a correct answer.
        answer: Generated answer text.

    Returns:
        Coverage score (0.0 to 1.0).
    """
    if not gold_keywords:
        return 1.0

    answer_lower = answer.lower()
    found = sum(1 for kw in gold_keywords if kw.lower() in answer_lower)
    return round(found / len(gold_keywords), 4)


def latency_percentile(latencies_ms: list[int], percentile: float = 95) -> float:
    """Compute latency percentile.

    Args:
        latencies_ms: List of latency values in milliseconds.
        percentile: Target percentile (e.g. 95 for P95).

    Returns:
        Latency at the given percentile in ms.
    """
    if not latencies_ms:
        return 0.0

    sorted_lat = sorted(latencies_ms)
    idx = int(len(sorted_lat) * percentile / 100)
    idx = min(idx, len(sorted_lat) - 1)
    return float(sorted_lat[idx])


def compute_query_metrics(
    result: EvalResult,
    expected_entities: list[str],
    gold_keywords: list[str],
) -> dict[str, float]:
    """Compute all applicable metrics for a single query result.

    Returns dict of metric_name → score.
    """
    # Extract entity names from subgraph nodes
    subgraph_nodes = result.subgraph.get("nodes", [])
    retrieved_entities = [
        n.get("name", "") for n in subgraph_nodes if n.get("name")
    ]

    metrics = {
        "entity_f1": entity_extraction_f1(expected_entities, retrieved_entities),
        "precision_at_10": retrieval_precision_at_k(
            expected_entities, result.seed_nodes
        ),
        "recall_at_10": retrieval_recall_at_k(expected_entities, result.seed_nodes),
        "keyword_coverage": keyword_coverage(gold_keywords, result.answer),
        "provenance_score": result.provenance_score,
        "latency_ms": float(result.latency_ms),
    }
    return metrics


def aggregate_metrics(results: list[EvalResult]) -> dict[str, float]:
    """Aggregate metrics across all results.

    Returns dict of metric_name → average score.
    """
    if not results:
        return {}

    metric_keys = set()
    for r in results:
        metric_keys.update(r.metrics.keys())

    aggregated = {}
    for key in metric_keys:
        values = [r.metrics[key] for r in results if key in r.metrics]
        if values:
            aggregated[key] = round(statistics.mean(values), 4)

    # Add latency percentiles
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    if latencies:
        aggregated["latency_p50"] = latency_percentile(latencies, 50)
        aggregated["latency_p95"] = latency_percentile(latencies, 95)
        aggregated["latency_p99"] = latency_percentile(latencies, 99)

    return aggregated
