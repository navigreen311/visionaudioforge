.PHONY: dev build stop clean logs db-shell redis-shell

dev:
	docker compose up -d

build:
	docker compose build

stop:
	docker compose down

clean:
	docker compose down -v

logs:
	docker compose logs -f

db-shell:
	docker compose exec db psql -U vaf

redis-shell:
	docker compose exec redis redis-cli
