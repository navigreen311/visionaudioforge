.PHONY: dev build stop clean logs db-shell redis-shell test test-unit test-integration test-coverage lint db-migrate db-revision

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

logs:
	docker compose logs -f

db-shell:
	docker compose exec db psql -U postgres

redis-shell:
	docker compose exec redis redis-cli

test:
	cd backend && python -m pytest tests/ -v

test-unit:
	cd backend && python -m pytest tests/ -v -m unit

test-integration:
	cd backend && python -m pytest tests/integration/ -v

test-coverage:
	cd backend && python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

lint:
	cd backend && python -m flake8 app/ || true

db-migrate:
	docker compose exec api alembic upgrade head

db-revision:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"
