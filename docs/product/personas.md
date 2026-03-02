# User Personas — graphrag-neo4j

**Date:** 2026-03-02

---

## Persona 1 — Alex, the ML Engineer

**Role:** Senior ML Engineer at a mid-size tech company
**Age:** 28–35
**Tech level:** High — comfortable with Python, PyTorch, Hugging Face, basic graph databases

### Background
Alex spends a lot of time researching which ML methods to use for new projects. They regularly scan Papers With Code, arXiv, and GitHub to find relevant methods, benchmarks, and datasets. The challenge: understanding *relationships* — which methods compete, which datasets are canonical for a task, which papers build on each other.

### Goals
- Quickly understand the landscape of methods for a given ML task
- Find which datasets are standard benchmarks for a problem
- Understand how methods relate to each other (variants, improvements)

### Pain Points
- Vector search returns similar text but loses relational context
- Hard to see "what came from what" in the research landscape
- Traditional RAG answers are hard to verify (no source transparency)

### How They Use graphrag-neo4j
- Types domain questions: *"What methods solve semantic segmentation?"*
- Explores the graph to understand relationships between nodes
- Uses the Cypher panel to understand *how* the answer was retrieved
- Learns from the project's architecture to apply Graph RAG in their own work

### Quote
> *"I don't just want a list of papers — I want to understand how they connect."*

---

## Persona 2 — Priya, the ML Researcher

**Role:** PhD student / Postdoc in Computer Vision
**Age:** 24–30
**Tech level:** High on ML theory, moderate on software engineering

### Background
Priya is writing papers and needs to do literature surveys. She needs to find all methods that address a specific task, what datasets they were evaluated on, and what scores they achieved. She currently does this manually on Papers With Code's website.

### Goals
- Run literature survey queries over the ML knowledge base
- Find benchmark datasets for her task area
- Identify which methods are "state of the art" on specific metrics

### Pain Points
- Papers With Code website requires many clicks to get relational info
- Can't ask natural language questions — must browse manually
- Hard to see cross-domain connections (e.g. method from NLP applied in CV)

### How They Use graphrag-neo4j
- Asks questions like *"Which papers introduced transformers for vision tasks?"*
- Uses graph visualization to see the research topology for her task area
- Explores related tasks and datasets she hadn't considered

### Quote
> *"I need to see the whole picture, not just one paper at a time."*

---

## Persona 3 — Jordan, the Technical Evaluator

**Role:** Engineering Manager or Senior Technical Recruiter
**Age:** 30–45
**Tech level:** Moderate — can read code, understands system design concepts

### Background
Jordan is evaluating Fandi's portfolio on GitHub. They want to understand the technical depth of the project — not just that it works, but that the engineer understands the *why* behind architectural decisions.

### Goals
- Assess the candidate's ML + backend + frontend breadth
- Understand if the candidate can build real, runnable systems
- Gauge understanding of modern AI/ML architecture patterns

### Pain Points
- Portfolio projects often "just work" without explaining the reasoning
- Hard to tell if engineer used a framework blindly or understood the core
- README rarely explains tradeoffs

### How They Use graphrag-neo4j
- Reads the README to understand the project at a glance
- Runs `docker compose up` to see it working live
- Asks example questions, sees the Cypher query to understand the retrieval
- Reviews the codebase to assess code quality and architecture

### Quote
> *"Show me something that works AND that you clearly understand."*
