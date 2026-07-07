SHELL := /bin/sh
COMPOSE := docker compose
DEV_FILES := -f docker-compose.yml -f docker-compose.dev.yml
STAGING_FILES := -f docker-compose.yml -f docker-compose.staging.yml
PROD_FILES := -f docker-compose.yml -f docker-compose.prod.yml
SERVICE ?= django
PREVIOUS_ENV_FILE ?=
UV := UV_CACHE_DIR=.uv-cache uv
DJANGO_UV := UV_CACHE_DIR=../../.uv-cache uv --project src/django
FASTAPI_UV := UV_CACHE_DIR=../../.uv-cache uv --project src/fastapi

.PHONY: up down restart restart-django restart-fastapi logs shell migrate reset-db seed-db build-dev clean debug-django debug-fastapi
.PHONY: lint test test-contract test-unit test-integration test-watch test-fast
.PHONY: lock-django lock-fastapi test-django test-fastapi scan-django scan-fastapi scan compose-check ci act-ci
.PHONY: prod-build prod-up prod-smoke backup restore rollback
.PHONY: shell-django

up:
	$(COMPOSE) $(DEV_FILES) up --build -d

down:
	$(COMPOSE) $(DEV_FILES) down

restart:
	$(COMPOSE) $(DEV_FILES) restart django fastapi

restart-django:
	$(COMPOSE) $(DEV_FILES) restart django

restart-fastapi:
	$(COMPOSE) $(DEV_FILES) restart fastapi

logs:
	$(COMPOSE) $(DEV_FILES) logs -f $(SERVICE)

shell:
	$(COMPOSE) $(DEV_FILES) exec $(SERVICE) /bin/sh

shell-django:
	$(COMPOSE) $(DEV_FILES) exec django /bin/sh -lc '. /opt/venv/bin/activate && export DJANGO_SETTINGS_MODULE=app.settings && exec /bin/sh'

migrate:
	$(COMPOSE) $(DEV_FILES) exec django python manage.py migrate

reset-db:
	$(COMPOSE) $(DEV_FILES) down --volumes
	$(COMPOSE) $(DEV_FILES) up -d postgres-django postgres-fastapi redis

seed-db:
	.docker/scripts/seed_db.sh

build-dev:
	$(COMPOSE) $(DEV_FILES) build

clean:
	$(COMPOSE) $(DEV_FILES) down --remove-orphans

debug-django:
	$(COMPOSE) $(DEV_FILES) run --service-ports django /opt/venv/bin/python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8090

debug-fastapi:
	$(COMPOSE) $(DEV_FILES) run --service-ports fastapi /opt/venv/bin/python -m debugpy --listen 0.0.0.0:5679 -m uvicorn app.main:app --host 0.0.0.0 --port 8099 --reload

lint:
	$(UV) run ruff check .
	cd src/django && UV_CACHE_DIR=../../.uv-cache uv run ruff check .
	cd src/fastapi && UV_CACHE_DIR=../../.uv-cache uv run ruff check .

test: test-contract test-django test-fastapi

test-contract:
	$(UV) run pytest tests

test-unit: test-django test-fastapi

test-integration:
	$(UV) run pytest tests -m "not integration"

test-watch:
	$(UV) run pytest-watch tests

test-fast:
	cd src/django && UV_CACHE_DIR=../../.uv-cache uv run pytest tests -n auto
	cd src/fastapi && UV_CACHE_DIR=../../.uv-cache uv run pytest tests -n auto

lock-django:
	cd src/django && UV_CACHE_DIR=../../.uv-cache uv lock

lock-fastapi:
	cd src/fastapi && UV_CACHE_DIR=../../.uv-cache uv lock

test-django:
	cd src/django && UV_CACHE_DIR=../../.uv-cache uv run pytest tests

test-fastapi:
	cd src/fastapi && UV_CACHE_DIR=../../.uv-cache uv run pytest tests

scan-django:
	cd src/django && UV_CACHE_DIR=../../.uv-cache uv run bandit -q -r app -x tests
	cd src/django && PIP_CACHE_DIR=../../.cache/pip UV_CACHE_DIR=../../.uv-cache uv run pip-audit --cache-dir ../../.cache/pip-audit/django --progress-spinner off

scan-fastapi:
	cd src/fastapi && UV_CACHE_DIR=../../.uv-cache uv run bandit -q -r app -x tests
	cd src/fastapi && PIP_CACHE_DIR=../../.cache/pip UV_CACHE_DIR=../../.uv-cache uv run pip-audit --cache-dir ../../.cache/pip-audit/fastapi --progress-spinner off

scan: scan-django scan-fastapi
	PIP_CACHE_DIR=.cache/pip $(UV) run pip-audit --cache-dir .cache/pip-audit --progress-spinner off
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-banner --redact || echo "gitleaks not installed; skipping secret scan"
	@command -v trivy >/dev/null 2>&1 && trivy config --quiet . || echo "trivy not installed; skipping container/config scan"

compose-check:
	$(COMPOSE) $(DEV_FILES) config >/dev/null
	$(COMPOSE) $(STAGING_FILES) config >/dev/null
	$(COMPOSE) $(PROD_FILES) config >/dev/null

ci: lint test test-integration scan compose-check

act-ci:
	act pull_request -W .github/workflows/ci.yml

prod-build:
	$(COMPOSE) $(PROD_FILES) build

prod-up:
	$(COMPOSE) $(PROD_FILES) up -d

prod-smoke:
	.docker/scripts/smoke.sh

backup:
	.docker/scripts/backup.sh

restore:
	.docker/scripts/restore.sh

rollback:
	@if [ -z "$(PREVIOUS_ENV_FILE)" ]; then echo "Set PREVIOUS_ENV_FILE=/path/to/previous.env"; exit 1; fi
	$(COMPOSE) --env-file $(PREVIOUS_ENV_FILE) $(PROD_FILES) up -d
