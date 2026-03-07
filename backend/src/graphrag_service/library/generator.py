"""
Context formatting for LLM prompts — builds structured text from graph data.
"""


def build_context(seed_nodes: list, edges: list) -> str:
    """Build a text context string from graph data for the LLM.

    Args:
        seed_nodes: list of dicts with keys: label, name, score
        edges: list of dicts with keys: from_id, to_id, type, properties (optional)
    """
    lines = ["=== GRAPH CONTEXT ===", "SEED NODES:"]
    for s in seed_nodes:
        label = s.get("label", "Node")
        name = s.get("name", "")
        score = s.get("score", 0.0)
        lines.append(f"  [{label}] {name} (score={score:.2f})")
    lines.append("\nRELATIONSHIPS:")
    for e in edges[:30]:
        props = f" {e['properties']}" if e.get("properties") else ""
        lines.append(f"  ({e['from_id']}) -[{e['type']}]-> ({e['to_id']}){props}")
    return "\n".join(lines)
