.PHONY: dev build test lint db-migrate clean

dev:
	docker compose up

build:
	docker compose build

test:
	docker compose exec api pytest backend/tests/ -v
	docker compose exec frontend npm run lint

lint:
	docker compose exec api python -m py_compile backend/app/main.py
	docker compose exec frontend npm run lint

db-migrate:
	docker compose exec api alembic upgrade head

db-revision:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
