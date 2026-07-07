# Main Thread Orchestrator Execution Plan

Authority source: `.agents/ORCHESTRATOR.md`
Working directory: `/Users/noshysmiles/www/pyapp-scaffold`

## Goal

Coordinate Development, CI/CD, and Production implementation into one Docker Compose only Python scaffold, preserving existing workflow files where possible and validating through shared local commands.

## Execution Order

- [ ] Create durable agent plans in `.agents/plan`.
- [ ] Add tests first for service behavior and repository contracts.
- [ ] Implement service-local Django project at `src/django/app` with `src/django/pyproject.toml` and `src/django/uv.lock`.
- [ ] Implement service-local FastAPI project at `src/fastapi/app` with `src/fastapi/pyproject.toml` and `src/fastapi/uv.lock`.
- [ ] Ensure root Python project files, if present, are repository tooling only and contain no Django/FastAPI runtime dependencies.
- [ ] Implement Dockerfiles, Compose overlays, Caddy configs, and environment templates.
- [ ] Implement Makefile and CI/CD workflow updates.
- [ ] Implement production configs and operations documentation.
- [ ] Generate service-local lockfiles.
- [ ] Run validation gates and fix failures.

## Cross-Agent Contracts

- Development owns local service ergonomics, app scaffolds, hot reload, debugging, and onboarding.
- CI/CD owns deterministic `uv` installs, `make` command parity, workflows, scans, image publishing, and `act`.
- Production owns hardened runtime settings, secure Caddy, HA configuration examples, observability, and runbooks.
- All agents share Docker Compose overlays and the `Makefile` interface.
- All agents must preserve `src/django/app` and `src/fastapi/app`; `django_app` and `fastapi_app` package names are explicitly invalid.

## Validation Gates

- [ ] `uv sync --locked --group dev --project src/django`
- [ ] `uv sync --locked --group dev --project src/fastapi`
- [ ] `make test-django`
- [ ] `make test-fastapi`
- [ ] `make lint`
- [ ] `make test`
- [ ] `make test-integration`
- [ ] `make scan`
- [ ] `make compose-check`
- [ ] `make ci`

## Stop Conditions

- Missing network access prevents service-local lockfile generation after escalation.
- Docker daemon unavailable prevents Docker-specific validation.
- A generated test reveals a conflict between agent specs that requires user choice.
