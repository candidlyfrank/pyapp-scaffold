# pyapp-scaffold

Docker Compose scaffold for a server-rendered frontend and two Python services:

- Next.js frontend on `localhost:3000` in development
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

- Integrated frontend: `https://pyapp.envx/`
- Authenticated SSR example: `https://pyapp.envx/account`
- Integrated Django admin: `https://pyapp.envx/admin/`
- Caddy ingress health: `https://pyapp.envx/health`
- Direct frontend debugging: `http://localhost:3000/`
- Django app: `http://localhost:8090/`
- Django health: `http://localhost:8090/health/`
- FastAPI app: `http://localhost:8099/`
- FastAPI health: `http://localhost:8099/health`
- FastAPI readiness: `http://localhost:8099/ready`
- FastAPI docs: `http://localhost:8099/docs`
- Django admin: `http://localhost:8090/admin/`
- Caddy FastAPI route: `http://localhost/fastapi/health`

Browser code calls Django through relative `/api/...` paths. Server-rendered frontend code uses the private `DJANGO_INTERNAL_URL=http://django:8090` and forwards only the incoming cookie header to that configured origin.

The frontend process health endpoint is `http://frontend:3000/api/health` on the private Compose network. It intentionally remains independent of Django; Caddy reserves public `/api/*` paths for Django.

## Validate

```sh
make ci
```

The shared CI entrypoint runs linting, tests, security checks, and Compose config validation.
