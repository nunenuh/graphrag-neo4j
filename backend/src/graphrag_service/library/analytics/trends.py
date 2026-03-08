"""Trend scoring for Methods and Tasks.

Computes growth rates based on paper counts over time windows.
"""

import json
from collections import defaultdict


def compute_trend_scores(
    entity_year_counts: dict[str, dict[str, int]],
    recent_year: str = "2024",
    previous_year: str = "2023",
) -> dict[str, float]:
    """Compute trend scores for entities based on year-over-year growth.

    trend_score = recent_count / max(previous_count, 1)

    A score > 1.0 means growth, < 1.0 means decline, 1.0 means stable.

    Args:
        entity_year_counts: Dict mapping entity_uid → {year: paper_count}.
        recent_year: The recent year for comparison.
        previous_year: The previous year for comparison.

    Returns:
        Dict mapping entity_uid → trend_score (float).
    """
    result: dict[str, float] = {}
    for uid, year_counts in entity_year_counts.items():
        recent = year_counts.get(recent_year, 0)
        previous = year_counts.get(previous_year, 0)
        score = recent / max(previous, 1)
        result[uid] = round(score, 4)
    return result


def compute_diffusion_paths(
    method_task_year_data: dict[str, list[dict]],
) -> dict[str, str]:
    """Compute diffusion paths for methods.

    A diffusion path shows which tasks a method was applied to over time.

    Args:
        method_task_year_data: Dict mapping method_uid → list of
            {'task': str, 'year': str, 'paper_count': int}.

    Returns:
        Dict mapping method_uid → JSON string of diffusion path.
    """
    result: dict[str, str] = {}
    for method_uid, entries in method_task_year_data.items():
        # Sort by year, then by paper count descending
        sorted_entries = sorted(
            entries, key=lambda e: (e.get("year", ""), -e.get("paper_count", 0))
        )
        result[method_uid] = json.dumps(sorted_entries)
    return result


def build_entity_year_counts(
    evaluations: list[dict],
    entity_type: str = "method",
) -> dict[str, dict[str, int]]:
    """Build entity→year→count mapping from evaluation data.

    Since PwC evaluations don't directly link to years,
    this builds counts from the evaluation structure.

    Args:
        evaluations: Raw evaluation JSON data.
        entity_type: 'method' or 'task'.

    Returns:
        Dict mapping entity_name → {year: count}.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for ev in evaluations:
        task_name = ev.get("task", "")
        if not task_name:
            continue

        for ds_entry in ev.get("datasets", []):
            for row in ds_entry.get("sota", {}).get("rows", []):
                method_name = row.get("model_name", "")
                if not method_name:
                    continue

                # Use dataset evaluation date if available, else "unknown"
                year = str(row.get("year", "unknown"))

                if entity_type == "method":
                    counts[method_name][year] += 1
                elif entity_type == "task":
                    counts[task_name][year] += 1

    return dict(counts)
