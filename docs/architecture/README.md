# Architecture

The scaffold uses Docker Compose only. The base Compose file defines shared services, while development, staging, and production overlays adjust runtime behavior for each environment.

## Architecture Guides

- [Document file handling and RAG readiness](document-file-handling-and-rag-readiness.md)

## Services

- `frontend`: Next.js App Router service on port `3000`, with standalone production output.
- `django`: Django service on port `8090`.
- `fastapi`: FastAPI service on port `8099`.
- `caddy`: reverse proxy for local and production-like routing.
- `postgres-django`: PostgreSQL 15 database for Django.
- `postgres-fastapi`: PostgreSQL 15 database for FastAPI.
- `redis`: Redis cache/session dependency.

## Request Routing and Authentication

Caddy is the only integrated public origin. It routes `/api/*`, `/admin/*`, `/static/*`, and `/media/*` to Django without stripping the path, retains `/fastapi/*` as a compatibility route, and sends every other route to Next.js. Staging and production publish only Caddy ports.

Django owns login, logout, session cookies, permissions, and CSRF validation. Browser mutations use relative Django URLs and send the CSRF cookie as `X-CSRFToken`. Server-rendered reads use `DJANGO_INTERNAL_URL=http://django:8090`, forward the incoming cookie explicitly, apply a timeout, and disable shared caching.

## Environment Split

Development intentionally uses relaxed defaults: HTTP, wildcard CORS, single Postgres instances, single Redis, hot reload, and debug ports.

Staging and production use production image targets, JSON logging, hardened container options, Caddy security headers, and immutable image references. The frontend production image runs as its built-in non-root user with a read-only root filesystem and `/tmp` provided by `tmpfs`.
