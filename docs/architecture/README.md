# Architecture

The scaffold uses Docker Compose only. The base Compose file defines shared services, while development, staging, and production overlays adjust runtime behavior for each environment.

## Services

- `django`: Django service on port `8090`.
- `fastapi`: FastAPI service on port `8099`.
- `caddy`: reverse proxy for local and production-like routing.
- `postgres-django`: PostgreSQL 15 database for Django.
- `postgres-fastapi`: PostgreSQL 15 database for FastAPI.
- `redis`: Redis cache/session dependency.

## Environment Split

Development intentionally uses relaxed defaults: HTTP, wildcard CORS, single Postgres instances, single Redis, hot reload, and debug ports.

Staging and production use production image targets, JSON logging, hardened container options, Caddy security headers, and immutable image references.
