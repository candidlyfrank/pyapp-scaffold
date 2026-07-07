# Production Agent Implementation Plan

Authority source: `.agents/AGENT_PRODUCTION.md`
Working directory: `/Users/noshysmiles/www/pyapp-scaffold`

## Goal

Add production-oriented Docker Compose overlays, hardened runtime settings, Caddy security, PostgreSQL/Redis HA configuration examples, observability hooks, and operational runbooks.

## Checklist

- [ ] Ensure Django production image runs `src/django/app` and never `src/django/django_app`.
- [ ] Ensure FastAPI production image runs `src/fastapi/app` and never `src/fastapi/fastapi_app`.
- [ ] Ensure Django production image installs from `src/django/pyproject.toml` and `src/django/uv.lock`.
- [ ] Ensure FastAPI production image installs from `src/fastapi/pyproject.toml` and `src/fastapi/uv.lock`.
- [ ] Add `docker-compose.staging.yml` as a production-like overlay.
- [ ] Add `docker-compose.prod.yml` with hardened service settings.
- [ ] Configure production containers as non-root with dropped capabilities and read-only filesystems where practical.
- [ ] Add Caddy staging and production configs with TLS-ready routing, security headers, restricted CORS, and rate-limit placeholders.
- [ ] Add PostgreSQL configuration examples for pooling/replication readiness.
- [ ] Add Redis Sentinel configuration examples.
- [ ] Add health and readiness endpoint coverage for Django and FastAPI.
- [ ] Add JSON logging and correlation ID support.
- [ ] Add OpenTelemetry-ready environment variables and docs.
- [ ] Add backup, restore, migration, deployment, rollback, monitoring, and incident runbooks.
- [ ] Add `make prod-build`, `make prod-up`, `make prod-smoke`, `make backup`, `make restore`, and `make rollback`.

## Validation

- [ ] `make compose-check`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.staging.yml config`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`
- [ ] Production command scan confirms no `django_app.settings` or `fastapi_app.main:app` references remain.
- [ ] `make prod-build` when Docker and network access are available
- [ ] `make prod-smoke` against a running production-like stack

## Risks

- PostgreSQL replication and Redis Sentinel are production-like examples in a single Compose repo, not a substitute for a fully managed HA platform.
- Production secrets manager, CORS origins, TLS domain names, RPO/RTO, and observability backend remain deployment-specific.
- Read-only filesystems require explicit writable temp/cache paths.
- Shared build context or root dependency installation can accidentally include the other service's dependencies or source in production images.

## Rollback

Rollback must use previous known-good immutable image tags or digests through Compose env files. Database migrations require a documented forward/backward compatibility decision before production rollout.
