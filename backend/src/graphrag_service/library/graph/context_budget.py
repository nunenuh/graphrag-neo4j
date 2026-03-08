"""Token-aware context budget management.

Allocates context budget across graph data, text, and summary sections.
"""

from dataclasses import dataclass

import tiktoken
from loguru import logger


@dataclass(frozen=True)
class ContextBudget:
    """Token budget allocation for LLM context."""

    total_tokens: int = 8000
    graph_pct: float = 0.40
    text_pct: float = 0.40
    summary_pct: float = 0.20

    @property
    def graph_tokens(self) -> int:
        return int(self.total_tokens * self.graph_pct)

    @property
    def text_tokens(self) -> int:
        return int(self.total_tokens * self.text_pct)

    @property
    def summary_tokens(self) -> int:
        return int(self.total_tokens * self.summary_pct)


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken.

    Args:
        text: Input text.
        model: Tiktoken encoding name.

    Returns:
        Number of tokens.
    """
    try:
        enc = tiktoken.get_encoding(model)
        return len(enc.encode(text))
    except Exception:
        # Rough fallback: ~4 chars per token
        return len(text) // 4


def truncate_to_budget(text: str, max_tokens: int, model: str = "cl100k_base") -> str:
    """Truncate text to fit within token budget.

    Args:
        text: Input text.
        max_tokens: Maximum allowed tokens.
        model: Tiktoken encoding name.

    Returns:
        Truncated text with marker if truncated.
    """
    try:
        enc = tiktoken.get_encoding(model)
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated = enc.decode(tokens[:max_tokens])
        return truncated + "\n... [truncated]"
    except Exception:
        # Fallback: character-based truncation (~4 chars per token)
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... [truncated]"


def allocate_context(
    seed_nodes: list[dict],
    edges: list[dict],
    budget: ContextBudget | None = None,
) -> str:
    """Build context string within token budget.

    Prioritizes seed nodes first, then relationships ordered by proximity.

    Args:
        seed_nodes: Seed nodes with label, name, score.
        edges: Relationship dicts with from_id, to_id, type, properties.
        budget: Token budget allocation. Uses defaults if None.

    Returns:
        Context string within token budget.
    """
    if budget is None:
        budget = ContextBudget()

    # Build graph section
    graph_lines = ["=== GRAPH CONTEXT ===", "SEED NODES:"]
    for s in seed_nodes:
        label = s.get("label", "Node")
        name = s.get("name", "")
        score = s.get("score", 0.0)
        graph_lines.append(f"  [{label}] {name} (score={score:.2f})")

    graph_lines.append("\nRELATIONSHIPS:")
    for e in edges:
        props = f" {e['properties']}" if e.get("properties") else ""
        graph_lines.append(
            f"  ({e['from_id']}) -[{e['type']}]-> ({e['to_id']}){props}"
        )

    graph_section = "\n".join(graph_lines)
    graph_section = truncate_to_budget(graph_section, budget.graph_tokens)

    # Summary section (brief overview)
    summary = (
        f"\n=== SUMMARY ===\n"
        f"Retrieved {len(seed_nodes)} seed nodes and {len(edges)} relationships."
    )
    summary = truncate_to_budget(summary, budget.summary_tokens)

    full_context = graph_section + summary
    # Final check against total budget
    full_context = truncate_to_budget(full_context, budget.total_tokens)

    logger.bind(
        tokens=count_tokens(full_context),
        budget=budget.total_tokens,
        seeds=len(seed_nodes),
        edges=len(edges),
    ).info("context_budget.allocated")

    return full_context
