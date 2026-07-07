# CI/CD Agent Implementation Plan

Authority source: `.agents/AGENT_CICD.md`
Working directory: `/Users/noshysmiles/www/pyapp-scaffold`

## Goal

Provide deterministic local and GitHub-hosted validation using `uv`, `make`, Docker Buildx, Docker Compose, security scans, immutable image publishing, and local `act` execution.

## Checklist

- [ ] Add `src/django/pyproject.toml` with Django Python 3.11 runtime and dev tooling.
- [ ] Generate and maintain `src/django/uv.lock`.
- [ ] Add `src/fastapi/pyproject.toml` with FastAPI Python 3.11 runtime and dev tooling.
- [ ] Generate and maintain `src/fastapi/uv.lock`.
- [ ] Keep root `pyproject.toml`, if present, limited to repository tooling only.
- [ ] Add Make targets required by the orchestrator: `lint`, `test`, `test-integration`, `scan`, `compose-check`, `ci`, `act-ci`.
- [ ] Add service-specific Make targets: `lock-django`, `lock-fastapi`, `test-django`, `test-fastapi`, `scan-django`, `scan-fastapi`.
- [ ] Update existing untracked workflows rather than deleting user-created workflow files.
- [ ] Ensure CI delegates to `make ci`.
- [ ] Ensure CI runs `uv sync --locked --project src/django` and `uv sync --locked --project src/fastapi` independently.
- [ ] Ensure CI fails if `src/django/django_app`, `src/fastapi/fastapi_app`, `django_app.settings`, or `fastapi_app.main:app` appear.
- [ ] Ensure publish workflow builds Django and FastAPI from service-local build contexts, their own Dockerfiles, and `production` targets.
- [ ] Ensure deploy workflow validates Compose overlays before handoff.
- [ ] Ensure rollback workflow delegates to documented `make rollback`.
- [ ] Add scanner-friendly configuration using Ruff, pytest, Bandit, pip-audit, gitleaks, and Trivy-compatible commands.
- [ ] Document local `act` requirements and expected secrets.

## Validation

- [ ] `uv sync --locked --group dev --project src/django`
- [ ] `uv sync --locked --group dev --project src/fastapi`
- [ ] `make test-django`
- [ ] `make test-fastapi`
- [ ] `make scan-django`
- [ ] `make scan-fastapi`
- [ ] `make lint`
- [ ] `make test`
- [ ] `make test-integration`
- [ ] `make scan`
- [ ] `make compose-check`
- [ ] `make ci`
- [ ] `make act-ci` when `act` is installed and Docker is available

## Risks

- Network access may be required to generate service-local `uv.lock` files.
- Local scanner binaries may not be installed; `make scan` should clearly report missing optional scanners where appropriate.
- `act` compatibility can vary by CPU architecture and local Docker setup.
- A single root lockfile can hide service dependency drift; CI must validate both service locks independently.

## Rollback

CI/CD changes are configuration-only. Reverting workflow and Makefile changes restores the previous validation behavior. Published release artifacts are immutable and should not be deleted by rollback commands.
