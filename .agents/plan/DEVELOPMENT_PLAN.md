# Development Agent Implementation Plan

Authority source: `.agents/AGENT_DEVELOPMENT.md`
Working directory: `/Users/noshysmiles/www/pyapp-scaffold`

## Goal

Build the local Docker Compose development experience for a Python 3.11 scaffold with Django on port `8090`, FastAPI on port `8099`, Caddy routing, PostgreSQL 15+, Redis, hot reload, debugger support, and repeatable `make` commands.

## Checklist

- [ ] Create Django app scaffold under `src/django/app`.
- [ ] Create FastAPI app scaffold under `src/fastapi/app`.
- [ ] Add `src/django/pyproject.toml` and `src/django/uv.lock` for the Django project.
- [ ] Add `src/fastapi/pyproject.toml` and `src/fastapi/uv.lock` for the FastAPI project.
- [ ] Ensure `src/django/django_app` and `src/fastapi/fastapi_app` do not exist.
- [ ] Ensure Django settings use `app.settings` and FastAPI commands use `app.main:app`.
- [ ] Add unit tests for both health endpoints.
- [ ] Add integration tests for expected service ports and Compose/service metadata.
- [ ] Add multi-stage Dockerfiles for both services with `development`, `builder`, and `production` targets.
- [ ] Add development entrypoint scripts for migrations, hot reload, and debug attach.
- [ ] Add `docker-compose.yml` and `docker-compose.dev.yml`.
- [ ] Add Caddy development routing without TLS, rate limiting, or strict CORS.
- [ ] Add committed development defaults in `.env.dev` and non-secret examples for staging/production.
- [ ] Add `.vscode/launch.json` for simultaneous Django and FastAPI debugging.
- [ ] Add Make targets for common local workflows: up, down, logs, shell, migrate, reset-db, seed-db, build-dev, clean, debug.
- [ ] Add service-isolated Make targets: `lock-django`, `lock-fastapi`, `test-django`, `test-fastapi`, `scan-django`, `scan-fastapi`.
- [ ] Add onboarding, debugging, and troubleshooting documentation.

## Validation

- [ ] `uv sync --locked --group dev --project src/django`
- [ ] `uv sync --locked --group dev --project src/fastapi`
- [ ] `make test-django`
- [ ] `make test-fastapi`
- [ ] `make lint`
- [ ] `make test`
- [ ] `make test-integration`
- [ ] `make compose-check`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.dev.yml config`
- [ ] Repository search confirms no `django_app.settings` or `fastapi_app.main:app` references remain.

## Risks

- Development defaults must not leak into staging or production overlays.
- Debug ports and database ports may conflict on developer machines.
- Testcontainers may not be available everywhere, so integration tests should first validate deterministic local artifacts.
- A shared root Python project can reintroduce import collisions; root tooling must not own service runtime dependencies or put both service package roots on one test `pythonpath`.

## Rollback

All development changes are file-based and can be reverted by removing the scaffold files. Destructive data operations must be explicit and limited to development volumes.
