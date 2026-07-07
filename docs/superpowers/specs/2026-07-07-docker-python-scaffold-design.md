# Docker Python Scaffold Design

## Context

The workspace is an empty scaffold directory containing `AGENT.md` and IDE metadata. The goal is to implement the AGENT.md target: a production-ready, Docker Compose-only Python environment with strong local development, CI/CD, and production operations foundations.

The directory is not currently a Git repository, so this spec cannot be committed here until Git is initialized or the files are moved into a repository.

## Chosen Approach

Build the full scaffold directly in this directory using practical defaults for unspecified infrastructure details. External deployment values such as production domains, registry names, secrets backend, backup retention, and RPO/RTO will be represented as documented placeholders and environment variables rather than invented real settings.

This approach is preferred over a minimal demo because the user explicitly requested execution of `AGENT.md`, which defines a broad scaffold rather than a narrow proof of concept.

## Architecture

The scaffold will use Docker Compose only. It will include:

- FastAPI service exposed on port `8000`.
- Django service exposed on port `8001`.
- Caddy reverse proxy exposed on ports `80` and `443`.
- PostgreSQL 15+ databases per service.
- Simplified development Redis and production-like Redis Sentinel.
- Staging and production Compose overlays that model hardening, pooling, replication, health checks, and operational practices.

The base Compose file will define shared service contracts. The development overlay will prioritize fast feedback: volume mounts, hot reload, debug ports, simple databases, simple Redis, relaxed Caddy, and development-only relaxed security. Staging and production overlays will add production-like behavior without introducing Kubernetes or non-Compose orchestration.

## Python And Dependency Management

Both services will use Python 3.11 and `uv`. A shared Dockerfile pattern will provide explicit `development`, `builder`, and `production` targets. Development targets include debug and reload tools. Production targets minimize runtime surface, run as non-root users, and use hardened settings where compatible.

The scaffold will include `pyproject.toml` files and placeholder lock files or generation instructions. If network access prevents lock generation during implementation, the Makefile and docs will explain how to generate `uv.lock`.

## Local Developer Experience

The Makefile will expose shared commands required by `AGENT.md`:

- `make lint`
- `make test`
- `make test-integration`
- `make scan`
- `make compose-check`
- `make ci`
- `make act-ci`

Additional developer commands will cover startup, shutdown, logs, shells, migrations, database reset/seed, image builds, cleanup, and debugger attachment. VS Code launch settings will support simultaneous FastAPI and Django debugging through separate debug ports.

## CI/CD

GitHub Actions will be the canonical CI/CD system and will delegate to Make targets wherever practical. Workflows will use least-privilege permissions, support local execution with `act`, and include linting, tests, integration checks, Compose validation, dependency scanning, secret scanning, image scanning, SBOM/provenance placeholders, release summaries, and Compose-based staging/production deployment templates.

Promotion and rollback will be modeled with immutable image tags or digests and Compose environment configuration updates.

## Production Operations

Production configuration will include Caddy TLS and security headers, strict CORS placeholders, request limits, health/readiness checks, non-root containers, dropped capabilities, read-only filesystems where practical, JSON logs, correlation IDs, OpenTelemetry configuration, backup/restore scripts or docs, migration commands, runbooks, alerting guidance, and dashboard placeholders.

Database high availability will be modeled with Compose services for primary/replica topology and PgBouncer. Redis high availability will be modeled with Redis Sentinel services. These are scaffolded operational patterns, not a substitute for environment-specific capacity planning.

## Error Handling And Validation

Services will validate required environment variables at startup. Health endpoints will be available for FastAPI and Django. Compose health checks will gate dependent services where practical. Make targets will fail fast on missing prerequisites and provide consistent local/CI behavior.

## Testing

The scaffold will include basic unit and integration tests for both services. Integration tests will be structured to run against Docker Compose services. The test setup will include factory/test fixture patterns and a place for Testcontainers-backed expansion.

## Assumptions

- This empty directory is the target implementation location.
- Docker, Docker Compose, `uv`, and GitHub Actions are the intended tools.
- External details remain placeholders unless supplied later.
- Docker Compose is the only orchestration mechanism.
- Git commits are skipped until the directory is initialized as a repository.
