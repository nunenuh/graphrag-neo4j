.PHONY: help setup env install install-backend install-frontend \
       neo4j neo4j-stop neo4j-logs neo4j-browser \
       schema download ingest ingest-all \
       backend frontend dev dev-stop \
       docker-up docker-down docker-build docker-logs \
       test test-backend lint clean clean-data \
       check-env check-neo4j status

# Default
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────

setup: env install ## Full first-time setup (env + install deps)
	@echo "✓ Setup complete. Next: make neo4j && make schema && make download && make ingest"

env: ## Create .env from .env.example (won't overwrite)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env — edit it and add your OPENAI_API_KEY"; \
	else \
		echo ".env already exists"; \
	fi

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend (Poetry)
	cd backend && poetry install

install-frontend: ## Install frontend (npm)
	cd frontend && npm install

# ──────────────────────────────────────────────
# Neo4j
# ──────────────────────────────────────────────

neo4j: ## Start Neo4j (docker)
	docker compose up neo4j -d
	@echo "Waiting for Neo4j to be healthy..."
	@until docker inspect --format='{{.State.Health.Status}}' graph-rag-neo4j 2>/dev/null | grep -q healthy; do \
		sleep 2; printf "."; \
	done
	@echo "\n✓ Neo4j ready — browser: http://localhost:7474 (neo4j/password123)"

neo4j-stop: ## Stop Neo4j
	docker compose stop neo4j

neo4j-logs: ## Tail Neo4j logs
	docker compose logs -f neo4j

neo4j-browser: ## Open Neo4j browser
	@echo "http://localhost:7474"
	@which xdg-open >/dev/null 2>&1 && xdg-open http://localhost:7474 || true

# ──────────────────────────────────────────────
# Data pipeline
# ──────────────────────────────────────────────

schema: check-neo4j ## Create Neo4j constraints + vector indexes
	cd backend && poetry run python src/library/graph/schema.py

download: ## Download Papers With Code data
	bash data/download.sh

ingest: check-env check-neo4j ## Ingest entities + relationships into Neo4j (~30 min)
	cd backend && poetry run python src/library/graph/ingest.py

ingest-all: neo4j schema download ingest ## Full pipeline: neo4j → schema → download → ingest

# ──────────────────────────────────────────────
# Development servers
# ──────────────────────────────────────────────

backend: check-env ## Start FastAPI dev server (port 8000)
	cd backend && NEO4J_URI=bolt://localhost:7687 poetry run uvicorn main:app --reload --app-dir src --port 8000

frontend: ## Start Vite dev server (port 5173)
	cd frontend && npm run dev

dev: ## Start backend + frontend in parallel
	@echo "Starting backend (8000) and frontend (5173)..."
	@make backend &
	@make frontend &
	@wait

dev-stop: ## Kill dev servers
	@-pkill -f "uvicorn main:app" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true
	@echo "✓ Dev servers stopped"

# ──────────────────────────────────────────────
# Docker (full stack)
# ──────────────────────────────────────────────

docker-up: ## Start all services (docker compose)
	docker compose up -d

docker-build: ## Build and start all services
	docker compose up --build -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail all service logs
	docker compose logs -f

# ──────────────────────────────────────────────
# Testing & quality
# ──────────────────────────────────────────────

test: test-backend ## Run all tests

test-backend: ## Run backend tests
	cd backend && poetry run pytest -v --cov=src

lint: ## Lint backend code
	cd backend && poetry run python -m py_compile src/main.py
	cd backend && poetry run python -m py_compile src/router.py
	cd backend && poetry run python -m py_compile src/core/config.py
	cd backend && poetry run python -m py_compile src/dbase/neo4j/client.py
	cd backend && poetry run python -m py_compile src/library/graph/schema.py
	cd backend && poetry run python -m py_compile src/library/graph/parser.py
	cd backend && poetry run python -m py_compile src/library/graph/ingest.py
	cd backend && poetry run python -m py_compile src/library/rag/embedder.py
	cd backend && poetry run python -m py_compile src/library/rag/retriever.py
	cd backend && poetry run python -m py_compile src/library/rag/generator.py
	@echo "✓ All files compile"

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv frontend/node_modules frontend/dist

clean-data: ## Remove downloaded data files
	rm -f data/*.json data/*.gz

clean-neo4j: ## Remove Neo4j data volume (DESTRUCTIVE)
	@echo "This will delete all Neo4j data. Press Ctrl+C to cancel."
	@sleep 3
	docker compose down -v

# ──────────────────────────────────────────────
# Health checks
# ──────────────────────────────────────────────

check-env:
	@if [ ! -f .env ]; then echo "ERROR: .env not found. Run: make env"; exit 1; fi
	@grep -q "sk-" .env 2>/dev/null || echo "WARNING: OPENAI_API_KEY may not be set in .env"

check-neo4j:
	@docker inspect --format='{{.State.Health.Status}}' graph-rag-neo4j 2>/dev/null | grep -q healthy \
		|| (echo "ERROR: Neo4j not running. Run: make neo4j"; exit 1)

status: ## Show status of all services
	@echo "=== Neo4j ==="
	@docker inspect --format='{{.State.Health.Status}}' graph-rag-neo4j 2>/dev/null || echo "not running"
	@echo "\n=== Backend ==="
	@curl -s http://localhost:8000/api/health 2>/dev/null || echo "not running"
	@echo "\n=== Frontend ==="
	@curl -s -o /dev/null -w "running (port 5173)" http://localhost:5173 2>/dev/null || echo "not running"
	@echo "\n=== Data ==="
	@ls -lh data/*.json 2>/dev/null || echo "no data files"
	@echo ""
