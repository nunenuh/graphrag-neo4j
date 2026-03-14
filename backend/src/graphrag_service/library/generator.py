"""
Context formatting for LLM prompts — builds structured text from graph data.
"""

from collections import defaultdict


# Edge types to prioritize in context (order matters)
_PRIORITY_EDGE_TYPES = ["AUTHORED", "CO_AUTHORED_WITH", "ADDRESSES", "USES_METHOD", "EVALUATED_ON"]


def build_context(
    seed_nodes: list,
    edges: list,
    nodes: list | None = None,
) -> str:
    """Build a text context string from graph data for the LLM.

    Args:
        seed_nodes: list of dicts with keys: label, name, score
        edges: list of dicts with keys: from_id, to_id, type, properties (optional)
        nodes: optional list of node dicts with keys: uid, label, name/title
    """
    # Build UID → name lookup from nodes
    uid_to_name: dict[str, str] = {}
    uid_to_label: dict[str, str] = {}
    if nodes:
        for n in nodes:
            uid = n.get("uid", "")
            if uid:
                uid_to_name[uid] = n.get("name") or n.get("title") or uid
                uid_to_label[uid] = n.get("label", "")

    def _resolve(uid: str) -> str:
        name = uid_to_name.get(uid, uid)
        label = uid_to_label.get(uid, "")
        return f"[{label}] {name}" if label else name

    lines = ["=== GRAPH CONTEXT ===", "SEED NODES:"]
    for s in seed_nodes:
        label = s.get("label", "Node")
        name = s.get("name", "")
        score = s.get("score", 0.0)
        lines.append(f"  [{label}] {name} (score={score:.2f})")

    # Group edges by type, prioritize important relationship types
    edges_by_type: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        edges_by_type[e.get("type", "UNKNOWN")].append(e)

    # Sort edge types: priority types first, then others alphabetically
    priority_set = set(_PRIORITY_EDGE_TYPES)
    sorted_types = [t for t in _PRIORITY_EDGE_TYPES if t in edges_by_type]
    sorted_types += sorted(t for t in edges_by_type if t not in priority_set)

    lines.append("\nRELATIONSHIPS:")
    edge_budget = 80
    shown = 0
    for edge_type in sorted_types:
        type_edges = edges_by_type[edge_type]
        lines.append(f"\n  {edge_type} ({len(type_edges)} total):")
        # Show up to 15 edges per type, within overall budget
        for e in type_edges[:15]:
            if shown >= edge_budget:
                break
            from_name = _resolve(e["from_id"])
            to_name = _resolve(e["to_id"])
            lines.append(f"    {from_name} -> {to_name}")
            shown += 1
        remaining = len(type_edges) - min(15, len(type_edges))
        if remaining > 0:
            lines.append(f"    ... and {remaining} more")
        if shown >= edge_budget:
            break

    return "\n".join(lines)
