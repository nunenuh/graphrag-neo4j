# Variables
POETRY := $(shell command -v poetry 2>/dev/null || echo "$(HOME)/.local/share/pypoetry/venv/bin/poetry")
PROJECT := graphrag_service
PORT ?= 8005
HOST ?= 0.0.0.0

# Version info
VERSION ?= latest
GIT_COMMIT = $(shell git rev-parse --short HEAD)
GIT_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)
BUILD_DATE = $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')

# Colors for terminal output
BLUE := \033[34m
GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
RESET := \033[0m

.PHONY: help setup env install install-backend install-frontend \
       neo4j neo4j-stop neo4j-logs neo4j-browser \
       schema download ingest ingest-authors ingest-all \
       run backend frontend dev dev-stop \
       docker-run docker-up docker-down docker-build docker-logs \
       test test-unit test-integration test-e2e test-coverage \
       lint format clean clean-data clean-neo4j \
       check-env check-neo4j status info

# Default target
help:
	@echo "$(BLUE)GraphRAG Service - Available Commands:$(RESET)"
	@echo ""
	@echo "$(GREEN)Setup:$(RESET)"
	@echo "  $(GREEN)make setup$(RESET)              - Full first-time setup (env + install deps)"
	@echo "  $(GREEN)make env$(RESET)                - Create .env from env.example"
	@echo "  $(GREEN)make install$(RESET)            - Install all dependencies"
	@echo "  $(GREEN)make install-backend$(RESET)    - Install backend (Poetry)"
	@echo "  $(GREEN)make install-frontend$(RESET)   - Install frontend (npm)"
	@echo ""
	@echo "$(GREEN)Neo4j:$(RESET)"
	@echo "  $(GREEN)make neo4j$(RESET)              - Start Neo4j (docker)"
	@echo "  $(GREEN)make neo4j-stop$(RESET)         - Stop Neo4j"
	@echo "  $(GREEN)make neo4j-logs$(RESET)         - Tail Neo4j logs"
	@echo ""
	@echo "$(GREEN)Data Pipeline:$(RESET)"
	@echo "  $(GREEN)make schema$(RESET)             - Create Neo4j constraints + vector indexes"
	@echo "  $(GREEN)make download$(RESET)           - Download Papers With Code data"
	@echo "  $(GREEN)make ingest$(RESET)             - Ingest entities + relationships (~30 min)"
	@echo "  $(GREEN)make ingest-all$(RESET)         - Full pipeline: neo4j -> schema -> download -> ingest"
	@echo ""
	@echo "$(GREEN)Development:$(RESET)"
	@echo "  $(GREEN)make run$(RESET)                - Start backend (8005) + frontend (5179)"
	@echo "  $(GREEN)make dev$(RESET)                - Alias for make run"
	@echo "  $(GREEN)make backend$(RESET)            - Start FastAPI dev server only (port 8005)"
	@echo "  $(GREEN)make frontend$(RESET)           - Start Vite dev server only (port 5179)"
	@echo "  $(GREEN)make dev-stop$(RESET)           - Kill dev servers"
	@echo ""
	@echo "$(GREEN)Testing & Quality:$(RESET)"
	@echo "  $(GREEN)make test$(RESET)               - Run all tests"
	@echo "  $(GREEN)make test-unit$(RESET)          - Run unit tests only"
	@echo "  $(GREEN)make test-integration$(RESET)   - Run integration tests only"
	@echo "  $(GREEN)make test-coverage$(RESET)      - Run tests with coverage report"
	@echo "  $(GREEN)make lint$(RESET)               - Run all linting checks"
	@echo "  $(GREEN)make format$(RESET)             - Auto-format code with black and isort"
	@echo ""
	@echo "$(GREEN)Docker:$(RESET)"
	@echo "  $(GREEN)make docker-run$(RESET)         - Start all services (neo4j + backend + frontend)"
	@echo "  $(GREEN)make docker-build$(RESET)       - Build and start all services"
	@echo "  $(GREEN)make docker-down$(RESET)        - Stop all services"
	@echo "  $(GREEN)make docker-logs$(RESET)        - Tail all service logs"
	@echo ""
	@echo "$(GREEN)CLI:$(RESET)"
	@echo "  $(GREEN)make cli-schema$(RESET)         - Create schema via CLI"
	@echo "  $(GREEN)make cli-ingest$(RESET)         - Run ingestion via CLI"
	@echo "  $(GREEN)make cli-status$(RESET)         - Check graph status via CLI"
	@echo ""
	@echo "$(GREEN)Utilities:$(RESET)"
	@echo "  $(GREEN)make clean$(RESET)              - Remove build artifacts and caches"
	@echo "  $(GREEN)make clean-data$(RESET)         - Remove downloaded data files"
	@echo "  $(GREEN)make clean-neo4j$(RESET)        - Remove Neo4j data volume (DESTRUCTIVE)"
	@echo "  $(GREEN)make status$(RESET)             - Show status of all services"
	@echo "  $(GREEN)make info$(RESET)               - Show project information"

# ──────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────

setup: env install ## Full first-time setup (env + install deps)
	@echo "$(GREEN)Setup complete. Next: make neo4j && make schema && make download && make ingest$(RESET)"

env: ## Create .env from env.example (won't overwrite)
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "$(GREEN)Created .env - edit it and add your OPENAI_API_KEY$(RESET)"; \
	else \
		echo "$(YELLOW).env already exists$(RESET)"; \
	fi

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend (Poetry)
	@echo "$(BLUE)Installing backend dependencies...$(RESET)"
	cd backend && $(POETRY) install --with dev
	@echo "$(GREEN)Backend installation complete!$(RESET)"

install-frontend: ## Install frontend (npm)
	@echo "$(BLUE)Installing frontend dependencies...$(RESET)"
	cd frontend && npm install
	@echo "$(GREEN)Frontend installation complete!$(RESET)"

# ──────────────────────────────────────────────
# Neo4j
# ──────────────────────────────────────────────

neo4j: ## Start Neo4j (docker)
	@echo "$(BLUE)Starting Neo4j...$(RESET)"
	docker compose -f docker/docker-compose.dev.yml up neo4j -d
	@echo "Waiting for Neo4j to be healthy..."
	@until docker inspect --format='{{.State.Health.Status}}' graph-rag-neo4j 2>/dev/null | grep -q healthy; do \
		sleep 2; printf "."; \
	done
	@echo "\n$(GREEN)Neo4j ready - browser: http://localhost:7474 (neo4j/password123)$(RESET)"

neo4j-stop: ## Stop Neo4j
	docker compose -f docker/docker-compose.dev.yml stop neo4j

neo4j-logs: ## Tail Neo4j logs
	docker compose -f docker/docker-compose.dev.yml logs -f neo4j

neo4j-browser: ## Open Neo4j browser
	@echo "http://localhost:7474"
	@which xdg-open >/dev/null 2>&1 && xdg-open http://localhost:7474 || true

# ──────────────────────────────────────────────
# Data pipeline
# ──────────────────────────────────────────────

schema: check-neo4j ## Create Neo4j constraints + vector indexes
	@echo "$(BLUE)Creating Neo4j schema...$(RESET)"
	cd backend && $(POETRY) run cli graph schema
	@echo "$(GREEN)Schema created!$(RESET)"

download: ## Download Papers With Code data
	@echo "$(BLUE)Downloading data...$(RESET)"
	bash data/download.sh
	@echo "$(GREEN)Download complete!$(RESET)"

ingest: check-env check-neo4j ## Ingest entities + relationships into Neo4j (~30 min)
	@echo "$(BLUE)Starting ingestion...$(RESET)"
	cd backend && $(POETRY) run cli graph ingest
	@echo "$(GREEN)Ingestion complete!$(RESET)"

ingest-authors: check-env check-neo4j ## Ingest authors with entity resolution
	cd backend && $(POETRY) run cli graph ingest-authors

ingest-all: neo4j schema download ingest ## Full pipeline: neo4j -> schema -> download -> ingest

# ──────────────────────────────────────────────
# Development servers
# ──────────────────────────────────────────────

run: check-env check-neo4j dev-stop ## Start backend (8005) + frontend (5179) in parallel
	@echo "$(BLUE)Starting backend (8005) and frontend (5179)...$(RESET)"
	@trap 'kill 0' EXIT; \
		(cd backend && APP_DEBUG=true $(POETRY) run dev) & \
		echo "Waiting for backend to be ready..." && \
		until curl -sf http://localhost:$(PORT)/api/v1/health/ping >/dev/null 2>&1; do sleep 1; done && \
		echo "$(GREEN)Backend ready! Starting frontend...$(RESET)" && \
		(cd frontend && npm run dev) & \
		wait

backend: check-env dev-stop ## Start FastAPI dev server only (port 8005)
	cd backend && APP_DEBUG=true $(POETRY) run dev

frontend: ## Start Vite dev server only (port 5179)
	cd frontend && npm run dev

dev: run ## Alias for 'make run'

dev-stop: ## Kill dev servers
	@-pkill -9 -f "uvicorn graphrag_service" 2>/dev/null || true
	@-pkill -9 -f "vite" 2>/dev/null || true
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		ss -tlnp 2>/dev/null | grep -q ":$(PORT) " || break; \
		sleep 0.5; \
	done
	@-fuser -k -9 $(PORT)/tcp 2>/dev/null || true
	@-fuser -k -9 5179/tcp 2>/dev/null || true
	@sleep 0.5
	@echo "$(GREEN)Dev servers stopped$(RESET)"

# ──────────────────────────────────────────────
# Docker (full stack)
# ──────────────────────────────────────────────

docker-run: docker-up ## Alias for docker-up (start all services)

docker-up: ## Start all services: neo4j + backend + frontend (docker compose)
	docker compose -f docker/docker-compose.dev.yml up -d
	@echo "$(GREEN)Services started! Backend: http://localhost:8005 | Frontend: http://localhost:3000$(RESET)"
	@echo "$(GREEN)Check logs with: make docker-logs$(RESET)"

docker-build: ## Build and start all services
	docker compose -f docker/docker-compose.dev.yml up --build -d
	@echo "$(GREEN)Services built and started!$(RESET)"

docker-down: ## Stop all services
	@docker compose -f docker/docker-compose.dev.yml down 2>/dev/null || true
	@docker compose -f docker/docker-compose.run.yml down 2>/dev/null || true
	@echo "$(GREEN)All services stopped!$(RESET)"

docker-logs: ## Tail all service logs
	docker compose -f docker/docker-compose.dev.yml logs -f

docker-restart: docker-down docker-up ## Restart all services

# ──────────────────────────────────────────────
# CLI commands
# ──────────────────────────────────────────────

cli-schema: check-neo4j ## Create schema via CLI
	cd backend && $(POETRY) run cli graph schema

cli-ingest: check-env check-neo4j ## Run ingestion via CLI
	cd backend && $(POETRY) run cli graph ingest

cli-ingest-resume: check-env check-neo4j ## Resume ingestion from last checkpoint
	cd backend && $(POETRY) run cli graph ingest --resume --skip-embedded

cli-ingest-status: ## Show ingestion progress
	cd backend && $(POETRY) run cli graph ingest-status

cli-status: ## Check graph status via CLI
	cd backend && $(POETRY) run cli graph status

cli-health: ## Health check via CLI
	cd backend && $(POETRY) run cli health check

cli-eval: check-env check-neo4j ## Run evaluation suite
	cd backend && $(POETRY) run cli eval run --output results/eval_report.json --markdown

cli-eval-queries: ## List evaluation queries
	cd backend && $(POETRY) run cli eval queries

# ──────────────────────────────────────────────
# Testing & quality
# ──────────────────────────────────────────────

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	cd backend && $(POETRY) run pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(RESET)"
	cd backend && $(POETRY) run pytest tests/unit/ -v

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(RESET)"
	cd backend && $(POETRY) run pytest tests/integration/ -v

test-e2e: ## Run E2E tests
	@echo "$(BLUE)Running E2E tests...$(RESET)"
	cd backend && $(POETRY) run pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	cd backend && $(POETRY) run pytest tests/ --cov=$(PROJECT) --cov-report=term-missing --cov-report=html

lint: ## Run all linting checks
	@echo "$(BLUE)Running linting checks...$(RESET)"
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/main.py
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/router.py
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/core/config.py
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/core/logging.py
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/core/auth.py
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/dbase/neo4j/client.py
	cd backend && $(POETRY) run python -m py_compile src/graphrag_service/shared/exceptions.py
	@echo "$(GREEN)All files compile!$(RESET)"

format: ## Auto-format code with black and isort
	@echo "$(BLUE)Formatting code...$(RESET)"
	cd backend && $(POETRY) run black src/ tests/
	cd backend && $(POETRY) run isort src/ tests/
	@echo "$(GREEN)Code formatting complete!$(RESET)"

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	@echo "$(BLUE)Cleaning up...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv frontend/node_modules frontend/dist
	@echo "$(GREEN)Cleanup complete!$(RESET)"

clean-data: ## Remove downloaded data files
	rm -f data/*.json data/*.gz

clean-neo4j: ## Remove Neo4j data volume (DESTRUCTIVE)
	@echo "$(RED)This will delete all Neo4j data. Press Ctrl+C to cancel.$(RESET)"
	@sleep 3
	docker compose -f docker/docker-compose.dev.yml down -v

# ──────────────────────────────────────────────
# Health checks
# ──────────────────────────────────────────────

check-env:
	@if [ ! -f .env ]; then echo "$(RED)ERROR: .env not found. Run: make env$(RESET)"; exit 1; fi
	@grep -q "OPENAI_API_KEY" .env 2>/dev/null || echo "$(YELLOW)WARNING: OPENAI_API_KEY may not be set in .env$(RESET)"

check-neo4j:
	@docker inspect --format='{{.State.Health.Status}}' graph-rag-neo4j 2>/dev/null | grep -q healthy \
		|| (echo "$(RED)ERROR: Neo4j not running. Run: make neo4j$(RESET)"; exit 1)

status: ## Show status of all services
	@echo "$(BLUE)=== Neo4j ===$(RESET)"
	@docker inspect --format='{{.State.Health.Status}}' graph-rag-neo4j 2>/dev/null || echo "not running"
	@echo "\n$(BLUE)=== Backend ===$(RESET)"
	@curl -s http://localhost:8005/api/v1/health/ping 2>/dev/null || echo "not running"
	@echo "\n$(BLUE)=== Frontend ===$(RESET)"
	@curl -s -o /dev/null -w "running (port 5179)" http://localhost:5179 2>/dev/null || echo "not running"
	@echo "\n$(BLUE)=== Data ===$(RESET)"
	@ls -lh data/*.json 2>/dev/null || echo "no data files"
	@echo ""

info: ## Show project information
	@echo "$(BLUE)Project Information:$(RESET)"
	@echo "$(GREEN)Project:$(RESET) $(PROJECT)"
	@echo "$(GREEN)Version:$(RESET) $(VERSION)"
	@echo "$(GREEN)Port:$(RESET) $(PORT)"
	@echo "$(GREEN)Git Branch:$(RESET) $(GIT_BRANCH)"
	@echo "$(GREEN)Git Commit:$(RESET) $(GIT_COMMIT)"
	@echo "$(GREEN)Python:$(RESET) $$(cd backend && $(POETRY) run python --version)"
	@echo "$(GREEN)Poetry:$(RESET) $$($(POETRY) --version)"
