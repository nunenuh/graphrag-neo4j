# graphrag-neo4j

Full-stack **Graph RAG** using Neo4j as a unified graph + vector store.
Ask natural language questions about the ML research landscape —
the system retrieves a knowledge subgraph and generates grounded answers.

## Why Graph RAG (not just RAG)

Traditional RAG retrieves *similar text chunks*.
This retrieves a *knowledge subgraph* — enabling multi-hop reasoning
that vector search cannot do alone.

## Stack

| Layer | Tech |
|-------|------|
| Graph + Vector DB | Neo4j 5.15 |
| Backend | FastAPI + Python 3.11 |
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui |
| LLM + Embeddings | OpenAI GPT-4o-mini + text-embedding-3-small |
| Visualization | react-force-graph-2d |
| Infra | Docker Compose |

## Quick Start

```bash
git clone https://github.com/nunenuh/graphrag-neo4j
cd graphrag-neo4j
cp .env.example .env      # add OPENAI_API_KEY
docker compose up neo4j -d
cd backend && poetry run python src/library/graph/schema.py
bash data/download.sh
poetry run python src/library/graph/ingest.py    # ~30 min
docker compose up --build
# Open: http://localhost:3000
```

## Example Questions

- *"What methods are used for object detection?"*
- *"Which papers introduced transformer-based NLP models?"*
- *"What datasets benchmark image segmentation?"*
- *"Find BERT variants and the tasks they solve."*
