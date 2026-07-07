# CI/CD-Focused Agent

Review and summarize pipeline, scanning, release, and deployment readiness.

## Validation Requirements
- **Dependency Management**: Installation via `uv` and deterministic builds using
  service-local locks: `src/django/uv.lock` and `src/fastapi/uv.lock`.
- **Docker Optimization**: Build cache optimization and multi-stage target validation.
- **Security Scanning**:
    - Pre-build dependency vulnerability scanning.
    - Container image vulnerability scanning.
    - Secret scanning.
    - Static analysis and linting.
- **Quality Gates**: Unit, integration, and migration checks.
- **Workflow Orchestration**:
    - Separate workflows for development, staging, and production.
    - Remote execution in GitHub CI/CD and local execution via `act`.
- **Release Strategy**:
    - Immutable image tagging and provenance.
    - SBOM generation.
    - Deployment promotion via updating Compose-based configurations.
    - Rollback via previous known-good image digests/tags.
- **Security**: Pipeline permissions using least privilege; environment-specific configuration validation.
- **Reporting**: Release artifacts and summaries (avoiding raw log dumps).

## Workflow Consistency
Validate that workflow jobs delegate to shared local commands (e.g., `make ci`, `make test`, `make scan`, `make compose-check`) to ensure local and remote execution remain repeatable and consistent.

## Service Project Independence
Validate that CI/CD treats Django and FastAPI as independent build and test
units:
- `uv sync --locked` must run independently for `src/django` and `src/fastapi`.
- CI must run Django tests from the Django project and FastAPI tests from the
  FastAPI project.
- Dependency vulnerability scans must inspect each service lockfile separately.
- Docker image builds must use service-local Dockerfiles and service-local build
  contexts or otherwise prove that root context does not reintroduce shared
  runtime dependency ownership.
- Image publishing must produce separate immutable Django and FastAPI images from
  their independent dependency locks.
- Root `pyproject.toml`, if present, may be used for orchestration tooling only
  and must not be the source of application runtime dependencies.
- CI should expose or validate service-specific commands such as
  `make lock-django`, `make lock-fastapi`, `make test-django`,
  `make test-fastapi`, `make scan-django`, and `make scan-fastapi`.
