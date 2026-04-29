.PHONY: help bootstrap infra infra-down backend worker frontend \
        test test-be test-fe test-engine lint lint-be lint-fe \
        fmt fmt-be fmt-fe typecheck check migrate migration build clean

# Default
help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------- Setup ----------
bootstrap: ## One-time: install backend venv, frontend deps, playwright browsers, pull images
	./scripts/bootstrap.sh

# ---------- Infra ----------
infra: ## Start postgres + redis (detached)
	docker compose up -d
	@echo "postgres :5432  redis :6379"

infra-down: ## Stop postgres + redis
	docker compose down

# ---------- Run ----------
backend: ## Run FastAPI on :8000 with reload
	cd backend && PYTHONPATH=.. .venv/bin/uvicorn app.main:app --reload --port 8000

worker: ## Run RQ worker (Phase 4+). OBJC_DISABLE_INITIALIZE_FORK_SAFETY is required on
        ## macOS — without it, RQ's fork() of a thread-touched ObjC runtime aborts the work-horse.
	cd backend && OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES PYTHONPATH=.. .venv/bin/rq worker audits --url $$(grep -E '^REDIS_URL=' ../.env | cut -d= -f2-)

frontend: ## Run Next.js on :3000
	cd frontend && npm run dev

# ---------- Test ----------
test: test-be test-engine test-fe ## Run all tests

test-be: ## Backend pytest
	cd backend && .venv/bin/pytest -v

test-engine: ## audit_engine pytest (run from project root for correct PYTHONPATH)
	backend/.venv/bin/pytest audit_engine/tests -v

test-fe: ## Frontend Playwright
	cd frontend && npm run test:e2e

# ---------- Lint / Format ----------
lint: lint-be lint-fe ## Lint everything

lint-be:
	cd backend && .venv/bin/ruff check .
	backend/.venv/bin/ruff check audit_engine

lint-fe:
	cd frontend && npm run lint

fmt: fmt-be fmt-fe ## Auto-fix lint and format

fmt-be:
	cd backend && .venv/bin/ruff check --fix . && .venv/bin/ruff format .

fmt-fe:
	cd frontend && npx eslint --fix . || true

typecheck: ## Frontend TypeScript typecheck
	cd frontend && npm run typecheck

check: lint typecheck test ## Full pre-push verification

# ---------- DB ----------
migrate: ## Apply all pending migrations
	cd backend && .venv/bin/alembic upgrade head

migration: ## Create migration: make migration name="add users table"
	@if [ -z "$(name)" ]; then echo "Usage: make migration name=\"description\""; exit 1; fi
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(name)"

# ---------- Build ----------
build: ## Build frontend production bundle
	cd frontend && npm run build

# ---------- Clean ----------
clean: ## Remove venv, node_modules, build artifacts
	rm -rf backend/.venv backend/.pytest_cache backend/.ruff_cache
	rm -rf frontend/node_modules frontend/.next frontend/test-results frontend/playwright-report
