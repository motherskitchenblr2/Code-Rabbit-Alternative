# =============================================================================
# Git-Fix Makefile - Common Development Commands
# =============================================================================
# Usage: make [target]
# =============================================================================

.PHONY: help deploy up down restart logs build test lint format clean install hooks db-shell api-shell

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN  := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# =============================================================================
# HELP
# =============================================================================
help: ## Show this help message
	@echo "$(CYAN)Git-Fix - Available Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# =============================================================================
# DEPLOYMENT
# =============================================================================
deploy: ## 🚀 Full 1-click deployment (./deploy.sh)
	@./deploy.sh

deploy-fg: ## 🚀 Deploy in foreground (see logs)
	@./deploy.sh --foreground

deploy-quick: ## ⚡ Quick restart without rebuild
	@./deploy.sh --skip-build

deploy-fg-quick: ## ⚡ Quick restart in foreground
	@./deploy.sh --skip-build --foreground

up: ## 📦 Start all services (detached)
	@docker compose up -d

down: ## 🛑 Stop all services
	@docker compose down

down-volumes: ## 🛑 Stop and remove volumes (⚠️ destroys data)
	@docker compose down -v

restart: ## 🔄 Restart all services
	@docker compose restart

# =============================================================================
# BUILD
# =============================================================================
build: ## 🔨 Build all Docker images
	@docker compose build

build-no-cache: ## 🔨 Build without cache
	@docker compose build --no-cache

build-api: ## Build only API image
	@docker compose build api

build-frontend: ## Build only frontend image
	@docker compose build frontend

build-worker: ## Build only worker image
	@docker compose build worker

# =============================================================================
# LOGS & DEBUGGING
# =============================================================================
logs: ## 📋 View all logs (follow)
	@docker compose logs -f

logs-api: ## View API logs
	@docker compose logs -f api

logs-frontend: ## View frontend logs
	@docker compose logs -f frontend

logs-worker: ## View worker logs
	@docker compose logs -f worker

logs-db: ## View database logs
	@docker compose logs -f postgres

logs-redis: ## View Redis logs
	@docker compose logs -f redis

logs-qdrant: ## View Qdrant logs
	@docker compose logs -f qdrant

ps: ## List running containers
	@docker compose ps

top: ## Show container resource usage
	@docker stats --no-stream

# =============================================================================
# SHELL ACCESS
# =============================================================================
api-shell: ## 🐚 Shell into API container
	@docker compose exec api bash

frontend-shell: ## Shell into frontend container
	@docker compose exec frontend sh

db-shell: ## 🐘 PostgreSQL shell
	@docker compose exec postgres psql -U gitfix -d gitfix

redis-shell: ## Redis CLI
	@docker compose exec redis redis-cli

qdrant-shell: ## Qdrant shell
	@docker compose exec qdrant sh

worker-shell: ## Worker shell
	@docker compose exec worker bash

# =============================================================================
# DATABASE
# =============================================================================
db-migrate: ## Run database migrations
	@docker compose exec api alembic upgrade head

db-migrate-create: ## Create new migration (usage: make db-migrate-create MSG="message")
	@docker compose exec api alembic revision --autogenerate -m "$(MSG)"

db-downgrade: ## Downgrade database one revision
	@docker compose exec api alembic downgrade -1

db-reset: ## ⚠️ Reset database (destroys data)
	@docker compose exec postgres psql -U gitfix -d gitfix -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@make db-migrate

db-backup: ## Backup database
	@docker compose exec postgres pg_dump -U gitfix gitfix > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved to backup_$(shell date +%Y%m%d_%H%M%S).sql"

db-restore: ## Restore database (usage: make db-restore FILE=backup.sql)
	@docker compose exec -T postgres psql -U gitfix -d gitfix < $(FILE)

# =============================================================================
# TESTING & QUALITY
# =============================================================================
test: ## 🧪 Run all tests
	@docker compose exec api pytest -v --cov=backend --cov-report=term-missing

test-unit: ## Run unit tests only
	@docker compose exec api pytest -v -m "not integration" --cov=backend

test-integration: ## Run integration tests
	@docker compose exec api pytest -v -m integration

test-coverage: ## Run tests with coverage report
	@docker compose exec api pytest --cov=backend --cov-report=html --cov-report=term-missing
	@echo "Coverage report in htmlcov/index.html"

test-watch: ## Run tests in watch mode
	@docker compose exec api pytest -v --watch

lint: ## 🔍 Run all linters
	@echo "$(CYAN)Running Ruff...$(NC)"
	@docker compose exec api ruff check backend/ scripts/
	@echo "$(CYAN)Running Black...$(NC)"
	@docker compose exec api black --check backend/ scripts/
	@echo "$(CYAN)Running MyPy...$(NC)"
	@docker compose exec api mypy backend/ scripts/ || true

format: ## ✨ Format code
	@docker compose exec api ruff check --fix backend/ scripts/
	@docker compose exec api black backend/ scripts/
	@echo "$(GREEN)Code formatted!$(NC)"

typecheck: ## Run type checker
	@docker compose exec api mypy backend/ scripts/

security-scan: ## 🔒 Run security scans
	@echo "$(CYAN)Running Bandit...$(NC)"
	@docker compose exec api bandit -r backend/ -f json -o bandit-results.json || true
	@echo "$(CYAN)Running Safety...$(NC)"
	@docker compose exec api safety check --json --output safety-results.json || true

# =============================================================================
# FRONTEND
# =============================================================================
frontend-install: ## Install frontend dependencies
	@docker compose exec frontend npm install

frontend-dev: ## Start frontend dev server
	@docker compose exec frontend npm run dev -- --host 0.0.0.0 --port 5173

frontend-build: ## Build frontend for production
	@docker compose exec frontend npm run build

frontend-lint: ## Lint frontend
	@docker compose exec frontend npm run lint

frontend-test: ## Run frontend tests
	@docker compose exec frontend npm run test

# =============================================================================
# GIT HOOKS
# =============================================================================
hooks-install: ## Install git hooks
	@python scripts/install_hooks.py

hooks-test: ## Test pre-commit hook
	@python backend/hooks/pre-commit.py

# =============================================================================
# CLEANUP
# =============================================================================
clean: ## 🧹 Clean up containers, images, volumes
	@docker compose down -v --rmi all --remove-orphans
	@docker system prune -f

clean-containers: ## Remove stopped containers
	@docker container prune -f

clean-images: ## Remove unused images
	@docker image prune -f

clean-volumes: ## Remove unused volumes
	@docker volume prune -f

clean-all: ## 🧹 Nuclear cleanup (everything)
	@docker compose down -v --rmi all --remove-orphans
	@docker system prune -af --volumes
	@echo "$(GREEN)Complete cleanup done$(NC)"

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================
dev: ## Start development environment (API + Frontend + Worker)
	@docker compose up -d api frontend worker redis postgres qdrant
	@echo "$(GREEN)Development environment started!$(NC)"
	@echo "  API:      http://localhost:5000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Flower:   http://localhost:5555"

dev-logs: ## View dev environment logs
	@docker compose logs -f api frontend worker

shell: ## Quick shell into API
	@docker compose exec api bash

# =============================================================================
# CI/CD SIMULATION
# =============================================================================
ci: lint test security-scan ## Run full CI pipeline locally

pre-commit: ## Run pre-commit checks
	@python backend/hooks/pre-commit.py

# =============================================================================
# PRODUCTION SIMULATION
# =============================================================================
prod-build: ## Build production images
	@docker compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up: ## Start production stack
	@docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production stack
	@docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# =============================================================================
# UTILITIES
# =============================================================================
env-check: ## Check environment configuration
	@echo "$(CYAN)Checking environment...$(NC)"
	@test -f .env && echo "$(GREEN)✓ .env exists$(NC)" || echo "$(RED)✗ .env missing$(NC)"
	@grep -q "dev-secret" .env && echo "$(YELLOW)⚠ Using default secrets$(NC)" || echo "$(GREEN)✓ Custom secrets$(NC)"
	@test -f .gitfix.yaml && echo "$(GREEN)✓ .gitfix.yaml exists$(NC)" || echo "$(YELLOW)⚠ .gitfix.yaml missing$(NC)"

ports: ## Show port mappings
	@echo "$(CYAN)Port Mappings:$(NC)"
	@echo "  5000  - API Server"
	@echo "  5173  - Frontend (Vite)"
	@echo "  5432  - PostgreSQL"
	@echo "  5555  - Flower (Celery)"
	@echo "  6379  - Redis"
	@echo "  6333  - Qdrant HTTP"
	@echo "  6334  - Qdrant gRPC"
	@echo "  5555  - Flower (Celery Monitoring)"

health: ## Check service health
	@echo "$(CYAN)Checking service health...$(NC)"
	@curl -sf http://localhost:5000/api/v1/health && echo "$(GREEN)✓ API healthy$(NC)" || echo "$(RED)✗ API unhealthy$(NC)"
	@curl -sf http://localhost:5173 >/dev/null && echo "$(GREEN)✓ Frontend healthy$(NC)" || echo "$(YELLOW)⚠ Frontend not accessible$(NC)"
	@docker compose exec -T postgres pg_isready -U gitfix && echo "$(GREEN)✓ PostgreSQL healthy$(NC)" || echo "$(RED)✗ PostgreSQL unhealthy$(NC)"
	@docker compose exec -T redis redis-cli ping | grep -q PONG && echo "$(GREEN)✓ Redis healthy$(NC)" || echo "$(RED)✗ Redis unhealthy$(NC)"
	@curl -sf http://localhost:6333/healthz && echo "$(GREEN)✓ Qdrant healthy$(NC)" || echo "$(RED)✗ Qdrant unhealthy$(NC)"

# =============================================================================
# ONE-COMMAND SHORTCUTS
# =============================================================================
start: up ## Alias for up
stop: down ## Alias for down
re: restart ## Alias for restart
b: build ## Alias for build
l: logs ## Alias for logs
s: ps ## Alias for ps
sh: api-shell ## Alias for api-shell
db: db-shell ## Alias for db-shell
t: test ## Alias for test