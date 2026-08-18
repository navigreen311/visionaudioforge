.PHONY: dev up smoke smoke-core build stop clean logs ps db-shell redis-shell test test-unit test-integration test-e2e test-coverage lint format migrate seed sdk-python-test sdk-js-build

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
dev:
	docker compose up

# Start and block until every service passes its healthcheck and both one-shot
# jobs (migrate, minio_init) have exited 0. Unlike `dev`, this returns non-zero
# if the stack does not actually come up.
up:
	docker compose up -d --build --wait --wait-timeout 900
	@docker compose ps

# The full verification: boots the stack, then asserts migrations applied,
# extensions exist, the bucket exists, the console is reachable through nginx,
# the auth boundary survives the proxy, and the worker is on the broker.
# This is exactly what CI runs.
smoke:
	./scripts/smoke-stack.sh

# Same assertions minus frontend and nginx — the api + db + redis + minio core.
smoke-core:
	./scripts/smoke-stack.sh --core

build:
	docker compose build

stop:
	docker compose down

ps:
	docker compose ps

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
# -U postgres was wrong: the db service is created as $$POSTGRES_USER, which
# defaults to vaf. `psql -U postgres` fails with "role does not exist".
db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-vaf} -d $${POSTGRES_DB:-vaf}

redis-shell:
	docker compose exec redis redis-cli

# Migrations run automatically as the `migrate` one-shot on every `up`; this is
# for re-running them by hand after adding a revision.
migrate:
	docker compose run --rm migrate alembic upgrade head

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
