# pyapp-scaffold

Docker Compose scaffold for two Python services:

- Django on `localhost:8090`
- FastAPI on `localhost:8099`
- Caddy reverse proxy on ports `80` and `443`
- PostgreSQL 15 per service
- Redis for cache/session-style dependencies

## Prerequisites

- Docker and Docker Compose
- `uv`
- `make`
- `act` for local GitHub Actions checks

## Start Development

```sh
uv sync --locked --group dev
make up
```

Open:

- Django app: `http://localhost:8090/`
- Django health: `http://localhost:8090/health/`
- FastAPI app: `http://localhost:8099/`
- FastAPI health: `http://localhost:8099/health`
- FastAPI readiness: `http://localhost:8099/ready`
- FastAPI docs: `http://localhost:8099/docs`
- Django admin: `http://localhost:8090/admin/`
- Caddy Django route: `http://localhost/django/health/`
- Caddy FastAPI route: `http://localhost/fastapi/health`

## Validate

```sh
make ci
```

The shared CI entrypoint runs linting, tests, security checks, and Compose config validation.
