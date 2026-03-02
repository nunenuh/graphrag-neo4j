# User Journey Maps — graphrag-neo4j

**Date:** 2026-03-02

---

## Journey 1 — ML Engineer Exploring a New Task Domain

**Persona:** Alex (ML Engineer)
**Scenario:** Alex is starting a new project on image segmentation and wants to understand the landscape before choosing a method.

```
STAGE         ACTION                          THOUGHT                        EMOTION
─────────────────────────────────────────────────────────────────────────────────────

Discovery     Sees the repo on GitHub         "Graph RAG + Neo4j?            🤔 Curious
              Reads README                     Interesting approach."

Setup         docker compose up               "One command — nice."          😊 Impressed
              Opens localhost:3000            "Clean UI."

First Query   Clicks example question:        "Let me see what it does       🧐 Engaged
              "What methods are used for       with something I know."
              image segmentation?"

Results       Sees answer in chat             "It mentions Mask R-CNN,       😮 Surprised
              Sees graph appear on right       UNet, SegFormer — correct."
              Sees orange seed nodes

Graph         Hovers over nodes               "I can see EVALUATED_ON        🤩 Impressed
Exploration   Sees edges labeled              edges — this is actual
              EVALUATED_ON, USED_FOR          relational reasoning."

Deep Dive     Expands Cypher panel            "It used vector search to      🧠 Learning
              Reads generated Cypher          find seeds, then Cypher
                                              to traverse. Clever."

Follow-up     Types custom question:          "Let me push it harder."       💪 Testing
              "Find BERT variants and
              their benchmark datasets"

Satisfaction  Gets accurate multi-hop         "This is genuinely useful.     ✅ Satisfied
              answer with graph               I should build something
                                              like this."
```

**Key moments:**
- ✅ One-command setup removes friction
- ✅ Graph visualization makes relationships tangible
- ✅ Cypher panel provides transparency (rare in RAG demos)
- ⚠️ Slow ingestion (30 min) is acceptable since it's one-time

---

## Journey 2 — Researcher Running a Literature Survey

**Persona:** Priya (ML Researcher)
**Scenario:** Priya needs to survey all datasets used for object detection benchmarking.

```
STAGE         ACTION                          THOUGHT                        EMOTION
─────────────────────────────────────────────────────────────────────────────────────

Arrival       Lands on localhost:3000         "This looks like a             🤔 Curious
                                              knowledge graph demo."

Query         Types: "What datasets           "This is exactly the type      ✍️ Focused
              are used to benchmark           of question I'd ask in
              object detection?"              my research."

Answer        Reads answer                    "COCO, Pascal VOC,             😊 Pleased
              Sees COCO, VOC, LVIS            ImageNet — yes, those
              nodes on the graph              are the canonical ones."

Verification  Clicks on COCO node             "I can verify — the node       ✅ Trusting
              Sees edges to tasks             links to Object Detection
              and methods                     as expected."

Discovery     Notices LVIS on the graph       "I didn't think to ask         💡 Discovery
              connected to Instance           about instance seg —
              Segmentation                    interesting connection."

Follow-up     Types: "Which methods           "Now I'm going deeper."        🔥 Engaged
              achieve highest mAP
              on COCO?"

Outcome       Gets ranked method list         "This saved me 2 hours         ✅ Satisfied
              with scores from graph          of manual browsing."
```

**Key moments:**
- ✅ Graph shows connections she didn't ask for — discovery value
- ✅ Cited entities are verifiable (not hallucinated)
- ⚠️ Results limited to PwC data subset (5k papers) — user should know this

---

## Journey 3 — Technical Evaluator Reviewing the Portfolio

**Persona:** Jordan (Engineering Manager)
**Scenario:** Jordan is evaluating Fandi's GitHub for a senior ML engineer position.

```
STAGE         ACTION                          THOUGHT                        EMOTION
─────────────────────────────────────────────────────────────────────────────────────

Discovery     Finds repo on GitHub            "Graph RAG with Neo4j —        🤔 Interested
              Reads README top section        that's a more advanced
                                              take than typical RAG demos."

Architecture  Reads architecture section      "Oh — vector search AND        😮 Interested
              in README                       graph traversal in one
                                              Cypher query. That's clever."

Setup         Follows Quick Start             "Docker Compose worked          😊 Pleased
              docker compose up               on first try. Good sign."

Live Demo     Asks example question           "Relevant answer with          👍 Positive
              Sees graph and answer           cited entities. Not
                                              hallucinating."

Code Review   Opens backend/rag/retriever.py "Clean code, good              ✅ Impressed
              Reads retriever logic           separation of concerns.
                                              He understands the domain."

Cypher Panel  Expands Cypher panel in UI      "He's showing the Cypher.      💯 Convinced
                                              That's explainability —
                                              he thought about the UX."

Decision      Bookmarks repo                  "This person understands       🎯 Decided
              Sends to team                   ML + backend + graph DB.
                                              Worth interviewing."
```

**Key moments:**
- ✅ README explains the *why* (Graph RAG > traditional RAG) up front
- ✅ Docker Compose setup works on first try
- ✅ Cypher panel shows technical transparency and UX thinking
- ✅ Code quality signals experience, not just tutorial-following
