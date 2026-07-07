# Docker Python Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker Compose-only Python scaffold with FastAPI, Django, Caddy, PostgreSQL, Redis, local developer tooling, GitHub Actions, and documented staging/production operations.

**Architecture:** The scaffold uses base Compose definitions plus development, staging, and production overlays. FastAPI and Django each own their app code, dependency metadata, tests, and Dockerfile. Shared scripts, Caddy configs, Make targets, CI workflows, and docs tie local and remote workflows to the same commands.

**Tech Stack:** Python 3.11, FastAPI, Django, uv, Docker Compose, Caddy, PostgreSQL 15, PgBouncer, Redis, Redis Sentinel, GitHub Actions, act, pytest, ruff, bandit, pip-audit, detect-secrets, Trivy.

## Global Constraints

- Use Docker Compose only.
- Do not use Kubernetes, Helm, Kustomize, Argo Rollouts, or Kubernetes-specific deployment manifests.
- Use GitHub Actions as the canonical CI/CD system.
- Workflows must run in GitHub-hosted CI and must also be runnable locally with `act`.
- GitHub Actions workflows must call shared local commands wherever practical.
- Minimum required Make targets: `make lint`, `make test`, `make test-integration`, `make scan`, `make compose-check`, `make ci`, `make act-ci`.
- Use Python 3.11.
- Use a portable Python 3.11 slim-bullseye base image where appropriate.
- Use `uv` for dependency management.
- FastAPI must be exposed on port `8000`.
- Django must be exposed on port `8001`.
- Caddy must expose ports `80` and `443`.
- Development mode uses simplified PostgreSQL and Redis, development images, debug tools, and hot reload.
- Staging and production remain Docker Compose overlays.
- This directory is not currently a Git repository; commit steps are skipped until Git is initialized.

---

## File Structure

- `Makefile`: single command surface used by humans and GitHub Actions.
- `.env.example`, `.env.development`, `.env.staging.example`, `.env.production.example`: environment contracts.
- `compose.yml`: shared Compose service definitions and networks.
- `compose.dev.yml`: local development overlay with hot reload, debug ports, and simple dependencies.
- `compose.staging.yml`: production-like overlay with pooling, replicas, Sentinel, and stricter proxy behavior.
- `compose.prod.yml`: hardened production overlay with non-root/read-only/drop-cap settings where practical.
- `services/fastapi/`: FastAPI app, tests, dependency metadata, Dockerfile, entrypoint.
- `services/django/`: Django app, tests, dependency metadata, Dockerfile, entrypoint.
- `caddy/`: development and production Caddy configs.
- `scripts/`: validation, scanning, database, release, backup, and local helper scripts.
- `.github/workflows/`: GitHub Actions for CI, security scanning, image publishing, and Compose-based deployment.
- `.vscode/launch.json`: debugger attachment configs.
- `docs/`: onboarding, local development, CI/CD, operations, rollback, troubleshooting, and runbooks.

---

### Task 1: Repository Skeleton And Command Surface

**Files:**
- Create: `.gitignore`
- Create: `.dockerignore`
- Create: `.env.example`
- Create: `.env.development`
- Create: `.env.staging.example`
- Create: `.env.production.example`
- Create: `Makefile`
- Create: `scripts/check-prereqs.sh`
- Create: `scripts/validate-env.sh`

**Interfaces:**
- Produces: `make` targets required by all later tasks.
- Produces: `scripts/validate-env.sh ENV_FILE SERVICE_NAME` returning exit code `0` for valid env files and non-zero for missing required keys.

- [ ] **Step 1: Create ignore and environment contract files**

Add `.gitignore` with Python, Docker, editor, coverage, and secret file patterns.
Add `.dockerignore` with Git, caches, virtualenvs, coverage, editor metadata, and local env files.
Add environment files with these exact keys:

```dotenv
ENV=development
FASTAPI_PORT=8000
DJANGO_PORT=8001
CADDY_HTTP_PORT=80
CADDY_HTTPS_PORT=443
FASTAPI_DATABASE_URL=postgresql+asyncpg://fastapi:fastapi@fastapi-db:5432/fastapi
DJANGO_DATABASE_URL=postgres://django:django@django-db:5432/django
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=http://localhost,http://localhost:8000,http://localhost:8001
LOG_LEVEL=DEBUG
OTEL_ENABLED=false
FASTAPI_SECRET_KEY=development-fastapi-secret
DJANGO_SECRET_KEY=development-django-secret
POSTGRES_PASSWORD=development-postgres-password
REDIS_PASSWORD=development-redis-password
```

- [ ] **Step 2: Create `scripts/validate-env.sh`**

Implement a POSIX shell script that checks the env file exists and verifies required keys: `ENV`, `FASTAPI_DATABASE_URL`, `DJANGO_DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`, `FASTAPI_SECRET_KEY`, `DJANGO_SECRET_KEY`.

- [ ] **Step 3: Create `scripts/check-prereqs.sh`**

Implement checks for `docker`, `docker compose`, `uv`, and optional `act`. Print one line per check and exit non-zero for missing required tools.

- [ ] **Step 4: Create `Makefile`**

Define these targets:

```make
.PHONY: help prereqs up down restart logs logs-fastapi logs-django shell-fastapi shell-django \
        migrate seed reset-db build clean lint test test-fast test-watch test-integration \
        scan compose-check ci act-ci

COMPOSE_DEV=docker compose --env-file .env.development -f compose.yml -f compose.dev.yml
COMPOSE_STAGING=docker compose --env-file .env.staging.example -f compose.yml -f compose.staging.yml
COMPOSE_PROD=docker compose --env-file .env.production.example -f compose.yml -f compose.prod.yml

help:
	@grep -E '^[a-zA-Z0-9_-]+:' Makefile | cut -d: -f1 | sort

prereqs:
	./scripts/check-prereqs.sh

up: prereqs
	$(COMPOSE_DEV) up --build

down:
	$(COMPOSE_DEV) down

restart:
	$(COMPOSE_DEV) restart

logs:
	$(COMPOSE_DEV) logs -f

logs-fastapi:
	$(COMPOSE_DEV) logs -f fastapi

logs-django:
	$(COMPOSE_DEV) logs -f django

shell-fastapi:
	$(COMPOSE_DEV) exec fastapi sh

shell-django:
	$(COMPOSE_DEV) exec django sh

migrate:
	$(COMPOSE_DEV) exec django uv run python manage.py migrate

seed:
	$(COMPOSE_DEV) exec django uv run python manage.py seed_dev

reset-db:
	$(COMPOSE_DEV) down -v
	$(COMPOSE_DEV) up -d fastapi-db django-db redis

build:
	$(COMPOSE_DEV) build

clean:
	$(COMPOSE_DEV) down -v --remove-orphans

lint:
	uv run ruff check services scripts
	uv run bandit -r services

test:
	uv run pytest services/fastapi/tests services/django/tests

test-fast:
	uv run pytest services/fastapi/tests services/django/tests -m 'not integration'

test-watch:
	uv run ptw services

test-integration:
	$(COMPOSE_DEV) up -d fastapi-db django-db redis
	uv run pytest -m integration

scan:
	./scripts/scan.sh

compose-check:
	docker compose -f compose.yml -f compose.dev.yml config >/dev/null
	docker compose -f compose.yml -f compose.staging.yml config >/dev/null
	docker compose -f compose.yml -f compose.prod.yml config >/dev/null

ci: lint test compose-check scan

act-ci:
	act -W .github/workflows/ci.yml
```

- [ ] **Step 5: Verify skeleton commands parse**

Run: `make help`
Expected: target names are printed.

Run: `./scripts/validate-env.sh .env.development local`
Expected: exits `0`.

Run: `make compose-check`
Expected: fails until Compose files exist; this is acceptable at this task boundary.

- [ ] **Step 6: Commit if Git is available**

Run: `git status --short`
Expected in current workspace: fatal error because this is not a Git repository. If Git has been initialized by then, commit with `git add . && git commit -m "chore: add scaffold command surface"`.

---

### Task 2: FastAPI Service

**Files:**
- Create: `services/fastapi/pyproject.toml`
- Create: `services/fastapi/uv.lock`
- Create: `services/fastapi/Dockerfile`
- Create: `services/fastapi/entrypoint.sh`
- Create: `services/fastapi/app/__init__.py`
- Create: `services/fastapi/app/config.py`
- Create: `services/fastapi/app/logging.py`
- Create: `services/fastapi/app/main.py`
- Create: `services/fastapi/tests/test_health.py`
- Create: `services/fastapi/tests/test_config.py`

**Interfaces:**
- Produces: ASGI app at `services.fastapi.app.main:app`.
- Produces: `GET /healthz` returning `{"status": "ok", "service": "fastapi"}`.
- Produces: `GET /readyz` returning `{"status": "ready", "service": "fastapi"}` when configuration loads.

- [ ] **Step 1: Write FastAPI health and config tests**

Create tests using `fastapi.testclient.TestClient` that assert `/healthz`, `/readyz`, and missing required settings behavior.

- [ ] **Step 2: Run FastAPI tests and confirm failure**

Run: `cd services/fastapi && uv run pytest tests -v`
Expected: failure because app files are not implemented or dependencies are not installed.

- [ ] **Step 3: Implement FastAPI dependency metadata**

Add `services/fastapi/pyproject.toml` with dependencies: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `asyncpg`, `redis`, `structlog`, `asgi-correlation-id`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`; dev dependencies: `pytest`, `httpx`, `ruff`, `bandit`, `debugpy`, `pytest-watch`, `factory-boy`, `testcontainers`.

Create `uv.lock` as an empty generated-lock marker with documentation comment only if network access prevents `uv lock`. Prefer running `uv lock` when available.

- [ ] **Step 4: Implement FastAPI app**

Create focused modules:

```python
# services/fastapi/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    env: str = "development"
    database_url: str
    redis_url: str
    log_level: str = "INFO"
    secret_key: str
    otel_enabled: bool = False
    cors_allowed_origins: str = "http://localhost"

    model_config = SettingsConfigDict(env_prefix="FASTAPI_", extra="ignore")

def get_settings() -> Settings:
    return Settings()
```

`main.py` must register correlation ID middleware, CORS middleware, `/healthz`, `/readyz`, and `/`.

- [ ] **Step 5: Add FastAPI Dockerfile targets**

Use `python:3.11-slim-bullseye` for `base`, install `uv`, create `development`, `builder`, and `production` targets, run as non-root in production, expose `8000`, and use `uvicorn` with reload in development.

- [ ] **Step 6: Verify FastAPI tests**

Run: `cd services/fastapi && uv run pytest tests -v`
Expected: health and config tests pass.

---

### Task 3: Django Service

**Files:**
- Create: `services/django/pyproject.toml`
- Create: `services/django/uv.lock`
- Create: `services/django/Dockerfile`
- Create: `services/django/entrypoint.sh`
- Create: `services/django/manage.py`
- Create: `services/django/config/__init__.py`
- Create: `services/django/config/settings.py`
- Create: `services/django/config/urls.py`
- Create: `services/django/config/asgi.py`
- Create: `services/django/config/wsgi.py`
- Create: `services/django/core/__init__.py`
- Create: `services/django/core/views.py`
- Create: `services/django/core/management/commands/seed_dev.py`
- Create: `services/django/tests/test_health.py`
- Create: `services/django/tests/test_settings.py`

**Interfaces:**
- Produces: Django app served on port `8001`.
- Produces: `GET /healthz/` returning `{"status": "ok", "service": "django"}`.
- Produces: `GET /readyz/` returning `{"status": "ready", "service": "django"}`.
- Produces: management command `seed_dev`.

- [ ] **Step 1: Write Django health and settings tests**

Use `django.test.Client` to assert health endpoints and settings derived from environment variables.

- [ ] **Step 2: Run Django tests and confirm failure**

Run: `cd services/django && uv run pytest tests -v`
Expected: failure because Django project files do not exist yet.

- [ ] **Step 3: Implement Django dependency metadata**

Add dependencies: `django`, `gunicorn`, `psycopg[binary]`, `dj-database-url`, `redis`, `django-cors-headers`, `structlog`, `asgi-correlation-id`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-django`; dev dependencies: `pytest`, `pytest-django`, `ruff`, `bandit`, `debugpy`, `pytest-watch`, `factory-boy`, `testcontainers`.

- [ ] **Step 4: Implement Django settings and health views**

Configure `INSTALLED_APPS`, `MIDDLEWARE`, CORS, database URL parsing, JSON logging, `ALLOWED_HOSTS`, and startup env validation. Implement health views returning `JsonResponse`.

- [ ] **Step 5: Add Django Dockerfile targets**

Use the same `base`, `development`, `builder`, and `production` target pattern as FastAPI. Development runs `python manage.py runserver 0.0.0.0:8001`; production runs Gunicorn or Uvicorn ASGI.

- [ ] **Step 6: Verify Django tests**

Run: `cd services/django && uv run pytest tests -v`
Expected: health and settings tests pass.

---

### Task 4: Compose And Caddy Runtime

**Files:**
- Create: `compose.yml`
- Create: `compose.dev.yml`
- Create: `compose.staging.yml`
- Create: `compose.prod.yml`
- Create: `caddy/Caddyfile.dev`
- Create: `caddy/Caddyfile.prod`
- Create: `caddy/security-headers.caddy`

**Interfaces:**
- Consumes: FastAPI Dockerfile target `development` and `production`.
- Consumes: Django Dockerfile target `development` and `production`.
- Produces: `docker compose -f compose.yml -f compose.dev.yml config` valid config.
- Produces: dev routes `/api/*` to FastAPI and `/django/*` to Django.

- [ ] **Step 1: Create base Compose services**

Define networks `app` and `data`, named volumes for databases and Redis, shared `x-healthcheck-defaults`, and base services: `fastapi`, `django`, `caddy`, `fastapi-db`, `django-db`, `redis`.

- [ ] **Step 2: Create development overlay**

Use build target `development`, bind mount service directories, expose `8000`, `8001`, `5678`, `5679`, `5432`, `5433`, `6379`, set relaxed CORS, enable debug logging, and use simple Redis.

- [ ] **Step 3: Create staging overlay**

Add PgBouncer services, Postgres replica services, Redis Sentinel services, production-like Caddy config, and stricter environment values. Keep deployment modeled by Compose only.

- [ ] **Step 4: Create production overlay**

Use image references from environment variables, production targets, `read_only: true` where writable temp mounts are supplied, `cap_drop: ["ALL"]`, `security_opt: ["no-new-privileges:true"]`, restart policies, health checks, resource limits, PgBouncer, replicas, Redis Sentinel, and Caddy TLS config.

- [ ] **Step 5: Create Caddy configs**

`Caddyfile.dev` uses HTTP-only local routes and no rate limiting. `Caddyfile.prod` imports security headers, enables TLS through Caddy automation, sets strict CORS from env, and applies request body limits.

- [ ] **Step 6: Verify Compose config**

Run: `make compose-check`
Expected: all Compose configs render successfully.

---

### Task 5: Tests, Scans, And Local Validation

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `pytest.ini`
- Create: `scripts/scan.sh`
- Create: `scripts/wait-for-services.sh`
- Modify: `Makefile`

**Interfaces:**
- Produces: root `uv run pytest` test entry point.
- Produces: `scripts/scan.sh` used by `make scan`.

- [ ] **Step 1: Create root Python tooling metadata**

Configure workspace-level dev dependencies: `pytest`, `ruff`, `bandit`, `pip-audit`, `detect-secrets`, `pytest-watch`, `httpx`, `requests`, `testcontainers`.

- [ ] **Step 2: Create pytest configuration**

Define markers `integration`, `slow`, and `unit`. Set `testpaths = services`.

- [ ] **Step 3: Create scan script**

Run `ruff`, `bandit`, `pip-audit`, `detect-secrets scan`, and `trivy fs .` when tools are available. For optional tools not installed locally, print a clear skip line and exit `0` only when required Python checks pass.

- [ ] **Step 4: Create service wait script**

Poll FastAPI `/healthz` and Django `/healthz/` with bounded retries for integration checks.

- [ ] **Step 5: Verify local checks**

Run: `make lint`
Expected: passes after dependencies are available.

Run: `make test`
Expected: unit tests pass after dependencies are available.

Run: `make scan`
Expected: required Python scans pass; optional external scanners either run or print explicit skip messages.

---

### Task 6: Developer Experience And Documentation

**Files:**
- Create: `.vscode/launch.json`
- Create: `README.md`
- Create: `docs/development.md`
- Create: `docs/debugging.md`
- Create: `docs/testing.md`
- Create: `docs/troubleshooting.md`
- Create: `docs/environment.md`

**Interfaces:**
- Consumes: Make targets and debug ports from earlier tasks.
- Produces: onboarding path from clone to running services.

- [ ] **Step 1: Add VS Code debugger config**

Define attach configs for FastAPI on port `5678`, Django on port `5679`, and a compound config for both services.

- [ ] **Step 2: Write README quickstart**

Document prerequisites, `make prereqs`, `make up`, expected URLs, `make test`, `make lint`, and shutdown.

- [ ] **Step 3: Write development docs**

Cover hot reload, logs, shells, migrations, seed/reset, ports, resource expectations, and development-only relaxed security.

- [ ] **Step 4: Write debugging docs**

Cover debugpy, breakpoints, path mappings, simultaneous debugging, and common attachment failures.

- [ ] **Step 5: Write testing docs**

Cover unit tests, integration tests, watch mode, Testcontainers expansion, factories, and fixture scope.

- [ ] **Step 6: Write troubleshooting docs**

Cover port conflicts, Docker daemon issues, database connectivity, hot reload, debugger attachment, permission errors, and cleanup.

- [ ] **Step 7: Verify docs reference real commands**

Run: `grep -R "make " README.md docs`
Expected: commands listed in docs correspond to Makefile targets.

---

### Task 7: CI/CD And act Support

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/security.yml`
- Create: `.github/workflows/release.yml`
- Create: `.github/workflows/deploy-compose.yml`
- Create: `.actrc`
- Create: `docs/ci-cd.md`
- Create: `scripts/image-tag.sh`
- Create: `scripts/write-release-summary.sh`

**Interfaces:**
- Consumes: Make targets from Task 1 and scan script from Task 5.
- Produces: GitHub Actions workflows runnable locally with `make act-ci`.

- [ ] **Step 1: Create CI workflow**

Use least privilege `permissions: contents: read`. Checkout code, install uv, set up Python 3.11, run `make ci`.

- [ ] **Step 2: Create security workflow**

Run `make scan`, Docker image scan jobs, secret scanning, SBOM generation with Syft when available, and upload concise artifacts.

- [ ] **Step 3: Create release workflow**

Build FastAPI and Django images, tag with git SHA and semantic tag when present, generate provenance/SBOM artifacts, and publish release summary without raw logs.

- [ ] **Step 4: Create Compose deployment workflow**

Use GitHub Environments `staging` and `production`, require immutable image tags or digests as inputs, validate Compose config, and document that host deployment is environment-specific.

- [ ] **Step 5: Add act support**

Create `.actrc` mapping Ubuntu runner to a compatible act image. Ensure `make act-ci` runs `.github/workflows/ci.yml`.

- [ ] **Step 6: Write CI/CD docs**

Document GitHub-hosted execution, local `act` prerequisites, secrets, environment inputs, release artifacts, image tagging, provenance, promotion, and rollback.

---

### Task 8: Production Operations And Runbooks

**Files:**
- Create: `docs/operations.md`
- Create: `docs/runbooks/backup-restore.md`
- Create: `docs/runbooks/rollback.md`
- Create: `docs/runbooks/migrations.md`
- Create: `docs/runbooks/incident-response.md`
- Create: `docs/observability.md`
- Create: `observability/otel-collector.yml`
- Create: `observability/prometheus.yml`
- Create: `observability/alerts.yml`
- Create: `scripts/backup-postgres.sh`
- Create: `scripts/restore-postgres.sh`
- Create: `scripts/rollback-compose.sh`
- Create: `scripts/migrate.sh`

**Interfaces:**
- Consumes: production Compose overlay and image tag/digest inputs.
- Produces: documented operational procedures and scripts with safe defaults.

- [ ] **Step 1: Write operations overview**

Document production assumptions: Docker Compose host, external DNS, Caddy-managed TLS, environment-provided secrets, immutable image tags/digests, backup storage path, and required human approval for production changes.

- [ ] **Step 2: Create backup and restore scripts**

Implement scripts that require explicit env file and service name arguments. Backups use `pg_dump`; restores require `CONFIRM_RESTORE=yes`.

- [ ] **Step 3: Create rollback script**

Implement a Compose rollback helper that requires env file, compose files, service name, and image digest/tag. It updates an override env file and runs `docker compose up -d SERVICE`.

- [ ] **Step 4: Create migration script**

Run Django migrations and FastAPI migration hook if present. Require environment validation before migration.

- [ ] **Step 5: Add observability configs**

Create OpenTelemetry collector config, Prometheus scrape config for service metrics endpoints, and alert rules for service down, high error rate, slow p95 latency, database down, and Redis Sentinel quorum issues.

- [ ] **Step 6: Write runbooks**

Document backup/restore, rollback, migration, incident response, dashboards, alerts, compliance evidence, and validation commands.

---

### Task 9: Final Verification And Consolidation

**Files:**
- Modify: docs as needed based on verification findings.
- Modify: scripts as needed based on verification findings.
- Modify: Compose files as needed based on verification findings.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: scaffold ready for local use and CI review.

- [ ] **Step 1: Render project tree**

Run: `find . -maxdepth 4 -type f | sort`
Expected: all planned files exist.

- [ ] **Step 2: Validate environment files**

Run: `./scripts/validate-env.sh .env.development development`
Expected: exits `0`.

- [ ] **Step 3: Validate Compose**

Run: `make compose-check`
Expected: exits `0`.

- [ ] **Step 4: Run static checks**

Run: `make lint`
Expected: exits `0` after dependencies are available.

- [ ] **Step 5: Run tests**

Run: `make test`
Expected: exits `0` after dependencies are available.

- [ ] **Step 6: Run scans**

Run: `make scan`
Expected: exits `0`; optional scanner skips are explicit.

- [ ] **Step 7: Start development stack when Docker is available**

Run: `make up`
Expected: Caddy on `80`, FastAPI on `8000`, Django on `8001`, hot reload enabled, debug ports exposed.

- [ ] **Step 8: Document verification limits**

If network access prevents lock generation or dependency installation, document exact commands to run locally: `uv lock`, `uv sync`, `make ci`, and `make up`.

- [ ] **Step 9: Commit if Git is available**

Run: `git status --short`
Expected in current workspace: fatal error because this is not a Git repository. If Git has been initialized by then, commit with `git add . && git commit -m "feat: add docker python scaffold"`.

---

## Self-Review

- Spec coverage: development, CI/CD, production, Docker Compose, Python services, Caddy, database, Redis, Make targets, `uv`, docs, debugging, scanning, operations, and verification are covered.
- Placeholder scan: no unresolved marker text is present. Environment-specific values are represented as documented variables and examples.
- Type consistency: service names, Make targets, health endpoints, ports, and script interfaces are consistent across tasks.
