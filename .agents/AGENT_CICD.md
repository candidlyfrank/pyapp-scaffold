# CI/CD-Focused Agent

Review and summarize pipeline, scanning, release, and deployment readiness.

## Validation Requirements
- **Dependency Management**: Installation via `uv` and deterministic builds using `uv.lock`.
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
