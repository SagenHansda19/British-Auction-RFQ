-include .env
API_PORT ?= 8000

infra:      # postgres + redis
	docker compose up -d --wait

install:    # backend deps
	cd backend && uv sync

migrate:    # run migrations
	cd backend && uv run alembic upgrade head

migration:  # make migration m="message"
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

seed:       # reset dev db with demo data
	cd backend && uv run python -m scripts.seed

api:
	cd backend && uv run uvicorn app.main:app --reload --port $(API_PORT)

worker:
	cd backend && uv run celery -A app.worker.celery_app worker --loglevel=INFO

beat:
	cd backend && uv run celery -A app.worker.celery_app beat --loglevel=INFO

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .

.PHONY: infra install migrate migration seed api worker beat test lint web-install web

web-install:
	cd frontend && npm install

web:
	cd frontend && npm run dev
