from openai import OpenAI
from core.config import settings
from library.rag.retriever import RetrievedSubgraph

_client = OpenAI(api_key=settings.openai_api_key)

SYSTEM = """You are a helpful assistant answering questions about ML research.
You receive structured context from a knowledge graph (Papers, Methods, Tasks, Datasets).
Use ONLY the provided context. Cite specific entities. If context is insufficient, say so."""


def _build_context(sg: RetrievedSubgraph) -> str:
    lines = ["=== GRAPH CONTEXT ===", "SEED NODES:"]
    for s in sg.seed_nodes:
        lines.append(f"  [{s.label}] {s.name} (score={s.score:.2f})")
    lines.append("\nRELATIONSHIPS:")
    for e in sg.edges[:30]:
        props = f" {e.properties}" if e.properties else ""
        lines.append(f"  ({e.from_id}) -[{e.type}]-> ({e.to_id}){props}")
    return "\n".join(lines)


def generate_answer(question: str, sg: RetrievedSubgraph) -> str:
    context = _build_context(sg)
    res = _client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return res.choices[0].message.content
