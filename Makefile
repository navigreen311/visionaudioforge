.PHONY: dev build stop clean logs db-shell redis-shell test test-unit test-integration test-e2e test-coverage lint format migrate seed sdk-python-test sdk-js-build

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
dev:
	docker compose up

build:
	docker compose build

stop:
	docker compose down

clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage frontend/.next

logs:
	docker compose logs -f

# ---------------------------------------------------------------------------
# Database & Redis
# ---------------------------------------------------------------------------
db-shell:
	docker compose exec db psql -U postgres

redis-shell:
	docker compose exec redis redis-cli

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.scripts.seed

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test:
	cd backend && python -m pytest tests/ -v

test-unit:
	cd backend && python -m pytest tests/ -v -m unit

test-integration:
	cd backend && python -m pytest tests/integration/ -v

test-e2e:
	cd backend && python -m pytest tests/integration/ -v -m e2e

test-coverage:
	cd backend && python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# ---------------------------------------------------------------------------
# Code Quality
# ---------------------------------------------------------------------------
lint:
	cd backend && python -m flake8 app/ || true

format:
	cd backend && python -m black app/ tests/ && python -m isort app/ tests/

# ---------------------------------------------------------------------------
# SDKs
# ---------------------------------------------------------------------------
sdk-python-test:
	cd sdks/python && python -m pytest tests/ -v

sdk-js-build:
	cd sdks/javascript && npm run build
