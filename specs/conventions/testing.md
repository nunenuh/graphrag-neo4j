# Testing Conventions — graphrag-neo4j

Test structure, naming rules, and patterns for unit, integration, e2e mock, and BDD tests.

---

## Test Directory Structure

```
tests/
├── conftest.py                      # Shared fixtures (client, mocks, test Neo4j)
├── unit/                            # Unit tests — mocked deps, mirrors src/ structure
│   ├── conftest.py
│   ├── library/
│   │   ├── rag/
│   │   │   ├── test_embedder.py
│   │   │   ├── test_retriever.py
│   │   │   └── test_generator.py
│   │   └── graph/
│   │       └── test_parser.py
│   ├── core/
│   │   └── test_config.py
│   └── dbase/
│       └── neo4j/
│           └── test_client.py
├── integration/                     # Integration tests — real Neo4j (test instance), mirrors src/
│   ├── conftest.py                  # Neo4j test client fixture
│   └── library/
│       └── graph/
│           ├── test_schema.py
│           ├── test_ingest.py
│           └── test_retriever_neo4j.py
└── e2e/
    ├── query/                       # Feature: POST /api/query
    │   ├── mock/
    │   │   ├── conftest.py
    │   │   └── test_query_mock.py   # FastAPI TestClient + mocked Neo4j + OpenAI
    │   └── bdd/
    │       ├── conftest.py
    │       ├── features/
    │       │   └── query.feature    # Gherkin scenarios
    │       └── test_query_bdd.py    # pytest-bdd step implementations (real services)
    ├── graph/                       # Feature: /api/graph/explore + /api/graph/schema
    │   ├── mock/
    │   │   └── test_graph_mock.py
    │   └── bdd/
    │       ├── features/
    │       │   └── graph.feature
    │       └── test_graph_bdd.py
    └── health/                      # Feature: /api/health
        ├── mock/
        │   └── test_health_mock.py
        └── bdd/
            ├── features/
            │   └── health.feature
            └── test_health_bdd.py
```

---

## Test Philosophy

| Layer | Mocked? | Speed | Purpose |
|-------|---------|-------|---------|
| `unit/` | Yes (all external deps) | Fast (<1s each) | Test logic in isolation |
| `integration/` | No (real Neo4j test DB) | Medium (1–5s) | Test DB queries and schema |
| `e2e/{feature}/mock/` | Yes (Neo4j + OpenAI) | Fast | Test full API surface with controlled data |
| `e2e/{feature}/bdd/` | **No** (real services) | Slow | BDD scenarios against real running stack |

---

## Tools & Dependencies

```toml
# pyproject.toml
[tool.poetry.group.test.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-cov = "^5.0"
pytest-bdd = "^7.0"           # BDD tests
httpx = "^0.27"               # FastAPI TestClient (async)
pytest-mock = "^3.12"         # mocker fixture
factory-boy = "^3.3"          # Test data factories
```

Run tests:
```bash
# All tests
pytest tests/ --cov=src --cov-report=term-missing

# By layer
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/query/mock/ -v
pytest tests/e2e/query/bdd/ -v    # Requires running stack

# Coverage gate
pytest tests/ --cov=src --cov-fail-under=80
```

---

## Unit Tests (`tests/unit/`)

Test one function/class in isolation. Mock **all** external dependencies (Neo4j, OpenAI).

### Naming

- File: `test_{module_name}.py`
- Class: `Test{ClassName}` (optional — use classes for grouping related tests)
- Function: `test_{what}_{condition}_{expected_result}`

```python
def test_slugify_with_spaces_returns_hyphenated(): ...
def test_batch_embed_calls_openai_with_correct_model(): ...
def test_parser_skips_papers_with_missing_title(): ...
```

### Example: `tests/unit/library/rag/test_embedder.py`

```python
"""Unit tests for library/rag/embedder.py"""
import pytest
from unittest.mock import MagicMock, patch

from library.rag.embedder import embed_text, batch_embed, EMBEDDING_MODEL, BATCH_SIZE


class TestEmbedText:
    def test_returns_list_of_floats(self, mock_openai):
        """embed_text returns a 1536-dim float list."""
        mock_openai.return_value = [0.1] * 1536
        result = embed_text("test text")
        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)

    def test_calls_correct_model(self, mock_openai_client):
        """embed_text always uses text-embedding-3-small."""
        embed_text("test")
        mock_openai_client.embeddings.create.assert_called_once()
        call_kwargs = mock_openai_client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == EMBEDDING_MODEL

    def test_retries_on_rate_limit(self, mock_openai_client):
        """embed_text retries up to MAX_RETRIES on RateLimitError."""
        import openai
        mock_openai_client.embeddings.create.side_effect = [
            openai.RateLimitError("rate limited", response=MagicMock(), body={}),
            MagicMock(data=[MagicMock(embedding=[0.1] * 1536)]),
        ]
        result = embed_text("test")
        assert len(result) == 1536
        assert mock_openai_client.embeddings.create.call_count == 2


class TestBatchEmbed:
    def test_preserves_order(self, mock_openai_client):
        """batch_embed returns embeddings in same order as input."""
        texts = ["first", "second", "third"]
        expected = [[1.0] * 1536, [2.0] * 1536, [3.0] * 1536]
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(index=i, embedding=emb) for i, emb in enumerate(expected)]
        )
        result = batch_embed(texts)
        assert result == expected

    def test_splits_into_batches(self, mock_openai_client):
        """batch_embed calls API ceil(n / BATCH_SIZE) times."""
        texts = ["text"] * (BATCH_SIZE + 1)  # 101 texts → 2 batches
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(index=i, embedding=[0.1] * 1536) for i in range(BATCH_SIZE + 1)]
        )
        batch_embed(texts)
        assert mock_openai_client.embeddings.create.call_count == 2
```

### Shared fixtures: `tests/conftest.py`

```python
"""Shared fixtures for all test layers."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for unit tests."""
    with patch("openai.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4jClient.run_query for unit tests."""
    with patch("dbase.neo4j.client.Neo4jClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.run_query.return_value = []
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_papers() -> list[dict]:
    """Sample Paper entities for testing."""
    return [
        {"id": "attention-is-all-you-need", "title": "Attention Is All You Need",
         "abstract": "We propose the Transformer...", "url": "https://...", "year": 2017},
        {"id": "bert", "title": "BERT", "abstract": "Pre-training...", "url": "https://...", "year": 2019},
    ]
```

---

## Integration Tests (`tests/integration/`)

Test against a **real Neo4j test instance**. Uses a separate test database — never the production database.

### Test Neo4j Setup

```python
# tests/integration/conftest.py
import pytest
from neo4j import GraphDatabase
from core.config import Settings

@pytest.fixture(scope="session")
def test_settings():
    """Settings pointing to test Neo4j instance."""
    return Settings(
        neo4j_uri="bolt://localhost:7688",  # Test port — different from prod 7687
        neo4j_user="neo4j",
        neo4j_password="test-password",
        openai_api_key="sk-test",  # Not used in Neo4j integration tests
    )

@pytest.fixture(scope="session")
def neo4j_test_client(test_settings):
    """Real Neo4j client connected to test instance."""
    from dbase.neo4j.client import Neo4jClient
    client = Neo4jClient(test_settings.neo4j_uri, test_settings.neo4j_user, test_settings.neo4j_password)
    yield client
    client.close()

@pytest.fixture(autouse=True)
def clean_neo4j(neo4j_test_client):
    """Wipe all nodes/edges before each test."""
    neo4j_test_client.run_query("MATCH (n) DETACH DELETE n")
    yield
    neo4j_test_client.run_query("MATCH (n) DETACH DELETE n")
```

### Example: `tests/integration/library/graph/test_schema.py`

```python
"""Integration tests for library/graph/schema.py against real Neo4j."""
import pytest
from library.graph.schema import setup_schema

def test_setup_schema_creates_vector_indexes(neo4j_test_client):
    """setup_schema creates all 4 vector indexes."""
    setup_schema(neo4j_test_client)
    result = neo4j_test_client.run_query(
        "SHOW INDEXES YIELD name WHERE name CONTAINS 'embeddings' RETURN name"
    )
    index_names = {row["name"] for row in result}
    assert "paper_embeddings" in index_names
    assert "method_embeddings" in index_names
    assert "task_embeddings" in index_names
    assert "dataset_embeddings" in index_names

def test_setup_schema_is_idempotent(neo4j_test_client):
    """Running setup_schema twice does not raise errors."""
    setup_schema(neo4j_test_client)
    setup_schema(neo4j_test_client)  # Should not raise
```

---

## E2E Mock Tests (`tests/e2e/{feature}/mock/`)

Test the full HTTP stack using FastAPI's `TestClient` with **mocked external services** (Neo4j + OpenAI). Fast, no running containers needed.

### Example: `tests/e2e/query/mock/test_query_mock.py`

```python
"""E2E mock tests for POST /api/query"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_services():
    """Mock Neo4j and OpenAI for all tests in this module."""
    with patch("router.retrieve") as mock_retrieve, \
         patch("router.generate_answer") as mock_generate:

        mock_retrieve.return_value = MagicMock(
            seed_nodes=[MagicMock(id="yolo", label="Method", name="YOLO", score=0.92)],
            nodes=[MagicMock(id="yolo", label="Method", name="YOLO", title="", description="")],
            edges=[],
            cypher_used="MATCH (seed) WHERE seed.id IN $seed_ids...",
        )
        mock_generate.return_value = "YOLO is used for object detection..."

        yield mock_retrieve, mock_generate


def test_query_returns_200_with_answer():
    response = client.post("/api/query", json={"question": "What is YOLO?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "YOLO is used for object detection..."


def test_query_returns_seed_nodes():
    response = client.post("/api/query", json={"question": "What is YOLO?"})
    data = response.json()
    assert len(data["seed_nodes"]) == 1
    assert data["seed_nodes"][0]["name"] == "YOLO"


def test_query_returns_latency_ms():
    response = client.post("/api/query", json={"question": "What is YOLO?"})
    data = response.json()
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] >= 0


def test_query_empty_question_returns_422():
    response = client.post("/api/query", json={"question": ""})
    assert response.status_code == 422


def test_query_missing_question_returns_422():
    response = client.post("/api/query", json={})
    assert response.status_code == 422
```

---

## BDD Tests (`tests/e2e/{feature}/bdd/`)

### What makes BDD tests different

| | Mock E2E | BDD E2E |
|--|---------|--------|
| Services | Mocked | **Real** (running Docker stack) |
| Data | Fixture data | **Real data** in test Neo4j |
| Speed | Fast | Slow (seconds per scenario) |
| Purpose | API surface | User-facing behavior |
| When to run | Every PR | Nightly / pre-release |

**BDD tests connect to a real running stack.** They require `docker compose up` before running.

### Gherkin Feature Files

```gherkin
# tests/e2e/query/bdd/features/query.feature

Feature: Graph RAG Query
  As a user of the graphrag-neo4j API
  I want to ask natural language questions about ML research
  So that I receive grounded answers with graph evidence

  Background:
    Given the Neo4j database contains ML research data
    And the API is running at "http://localhost:8000"

  Scenario: Ask about object detection methods
    Given I have a question "What methods are used for object detection?"
    When I send a POST request to "/api/query"
    Then the response status is 200
    And the response contains a non-empty "answer"
    And the response contains at least 1 seed node
    And at least one seed node has label "Method"
    And the response contains "cypher_used"
    And "latency_ms" is a positive integer

  Scenario: Empty question is rejected
    Given I have a question ""
    When I send a POST request to "/api/query"
    Then the response status is 422

  Scenario: Answer references entities from seed nodes
    Given I have a question "What datasets benchmark image classification?"
    When I send a POST request to "/api/query"
    Then the response status is 200
    And at least one seed node has label "Dataset"
    And the "answer" mentions at least one seed node name
```

```gherkin
# tests/e2e/health/bdd/features/health.feature

Feature: API Health Check
  As an operator
  I want to check the health of the API and Neo4j connection
  So that I can monitor system availability

  Scenario: All services healthy
    Given the API and Neo4j are running
    When I send a GET request to "/api/health"
    Then the response status is 200
    And the response "status" is "ok"
    And the response "neo4j" is "connected"

  Scenario: API is up but Neo4j is down
    Given the API is running but Neo4j is unavailable
    When I send a GET request to "/api/health"
    Then the response status is 200
    And the response "status" is "ok"
    And the response "neo4j" is "error"
```

### Step Implementations

```python
# tests/e2e/query/bdd/test_query_bdd.py
"""BDD step implementations for query.feature"""
import httpx
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios("features/query.feature")

BASE_URL = "http://localhost:8000"  # Real running stack


@pytest.fixture
def context():
    """Shared state between steps in a scenario."""
    return {}


@given(parsers.parse('I have a question "{question}"'))
def have_question(context, question):
    context["question"] = question


@given("the API is running at \"http://localhost:8000\"")
def api_running():
    """Verify the API is reachable before running scenarios."""
    try:
        response = httpx.get(f"{BASE_URL}/api/health", timeout=5)
        assert response.status_code == 200, f"API not healthy: {response.json()}"
    except httpx.ConnectError:
        pytest.skip("API is not running — skipping BDD tests (run: docker compose up)")


@given("the Neo4j database contains ML research data")
def neo4j_has_data():
    """Verify Neo4j has data loaded (ingestion was run)."""
    response = httpx.get(f"{BASE_URL}/api/graph/schema", timeout=5)
    data = response.json()
    assert "Paper" in data["node_labels"], "Neo4j has no Paper nodes — run ingestion first"


@when(parsers.parse('I send a POST request to "{path}"'))
def send_post_request(context, path):
    response = httpx.post(
        f"{BASE_URL}{path}",
        json={"question": context["question"]},
        timeout=30,  # RAG pipeline can take ~3-5s
    )
    context["response"] = response


@when(parsers.parse('I send a GET request to "{path}"'))
def send_get_request(context, path):
    context["response"] = httpx.get(f"{BASE_URL}{path}", timeout=10)


@then(parsers.parse("the response status is {status_code:d}"))
def check_status_code(context, status_code):
    assert context["response"].status_code == status_code, \
        f"Expected {status_code}, got {context['response'].status_code}: {context['response'].text}"


@then(parsers.parse('the response contains a non-empty "{field}"'))
def check_field_non_empty(context, field):
    data = context["response"].json()
    assert field in data, f"Field '{field}' missing from response"
    assert data[field], f"Field '{field}' is empty"


@then(parsers.parse("the response contains at least {count:d} seed node"))
def check_seed_node_count(context, count):
    data = context["response"].json()
    assert len(data.get("seed_nodes", [])) >= count


@then(parsers.parse('at least one seed node has label "{label}"'))
def check_seed_node_label(context, label):
    data = context["response"].json()
    labels = [sn["label"] for sn in data.get("seed_nodes", [])]
    assert label in labels, f"No seed node with label '{label}'. Got: {labels}"


@then(parsers.parse('the response contains "{field}"'))
def check_field_exists(context, field):
    data = context["response"].json()
    assert field in data


@then('"latency_ms" is a positive integer')
def check_latency(context):
    data = context["response"].json()
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] > 0


@then(parsers.parse('the response "{field}" is "{expected_value}"'))
def check_field_value(context, field, expected_value):
    data = context["response"].json()
    assert data[field] == expected_value


@then('the "answer" mentions at least one seed node name')
def answer_mentions_seed_node(context):
    data = context["response"].json()
    answer = data["answer"].lower()
    seed_names = [sn["name"].lower() for sn in data["seed_nodes"]]
    assert any(name in answer for name in seed_names), \
        f"Answer '{answer[:100]}...' doesn't mention any seed node: {seed_names}"
```

### Running BDD Tests

```bash
# Requires: docker compose up (full stack running)
pytest tests/e2e/query/bdd/ -v

# With detailed Gherkin output
pytest tests/e2e/query/bdd/ -v --gherkin-terminal-reporter

# Skip if stack not running (useful in CI)
pytest tests/e2e/ --ignore=tests/e2e/*/bdd/ -v  # Skip all BDD

# Run only BDD
pytest tests/e2e/ -k "bdd" -v
```

**CI Strategy:**
```yaml
# .github/workflows/ci.yml
jobs:
  unit-and-integration:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src
      - name: Start test Neo4j
        run: docker compose up neo4j -d && sleep 10
      - name: Run integration tests
        run: pytest tests/integration/ -v
      - name: Run e2e mock tests
        run: pytest tests/e2e/ -k "mock" -v

  bdd:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # Only on main branch
    steps:
      - name: Start full stack
        run: docker compose up --build -d && sleep 30
      - name: Run BDD tests
        run: pytest tests/e2e/ -k "bdd" -v
```

---

## Test Data Factories

Use `factory-boy` for generating consistent test entities:

```python
# tests/factories.py
import factory

class PaperFactory(factory.DictFactory):
    id = factory.Sequence(lambda n: f"paper-{n}")
    title = factory.Sequence(lambda n: f"Paper {n}: Test Title")
    abstract = "This paper proposes a method for..."
    url = factory.LazyAttribute(lambda o: f"https://paperswithcode.com/paper/{o.id}")
    year = 2023

class MethodFactory(factory.DictFactory):
    id = factory.Sequence(lambda n: f"method-{n}")
    name = factory.Sequence(lambda n: f"Method {n}")
    description = "A machine learning method for..."

# Usage in tests
papers = PaperFactory.create_batch(5)
paper = PaperFactory(title="Custom Title", year=2021)
```

---

## Coverage Requirements

| Layer | Min Coverage |
|-------|-------------|
| `library/rag/embedder.py` | 90% |
| `library/rag/retriever.py` | 85% |
| `library/rag/generator.py` | 85% |
| `library/graph/parser.py` | 90% |
| `router.py` | 80% |
| Overall backend | **80%** |

```bash
pytest tests/unit/ tests/integration/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-fail-under=80
```
