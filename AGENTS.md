# Production-Ready Docker-Based Python Environment

Use Codex subagents to design, review, and validate a production-ready Docker-based Python development environment. The main thread coordinates the work, waits for every requested subagent result, and returns only consolidated summaries.

## Main Thread Orchestration

Dispatch three subagents in parallel:

1. **Development-focused agent:** hot-reload, debugging, local tooling, test feedback loops, developer onboarding.
2. **CI/CD-focused agent:** pipelines, vulnerability scanning, image publishing, deployment workflows, release gates.
3. **Production-focused agent:** security, observability, reliability, operations, compliance validation.

This is an implementation task. First use subagents to plan and identify risks. Create a plan for each subagent with a checklist, then execute the approved planned work in the current workspace. Wait for all subagents before consolidating, provide incremental summaries, ask for approval when creating and updating any files.

After the main thread approves the execution plan, implementation subagents may edit files inside the current workspace, run local validation commands, and create the requested scaffold. They must ask before destructive actions, deployment actions, network access, or writes outside the workspace.

The main thread must explicitly wait until all requested subagents return before consolidating results. Do not produce the final answer early. If a subagent is still running, continue waiting or ask for permission to actively steer it.

The main thread may directly steer a running subagent, stop it, or close completed agent threads when needed. Use steering when scope drifts, stop a subagent when its result is no longer needed or it is blocked, and close completed agent threads after their summaries have been captured.

## Return Format

Subagents must return summaries, not raw command output. Summaries should include:

- Decisions made
- Risks found
- Recommended changes
- Validation performed
- Open questions or blockers

Do not paste raw logs, raw scanner output, raw test output, or long command transcripts. Summarize the evidence and include concise references only where useful.

## Reasoning Effort

Use reasoning effort according to task complexity:

- **High reasoning effort:** architecture decisions, security reviews, compliance validation, production risk assessment, reliability trade-offs.
- **Medium reasoning effort:** implementation details, Docker/Compose structure, CI/CD structure, deployment workflow design, dependency management.
- **Low reasoning effort:** documentation review, file structure validation, naming checks, formatting checks, simple consistency checks.

## Execution Decisions

This scaffold must be implemented with Docker Compose only. Do not use Kubernetes, Helm, Kustomize, Argo Rollouts, or Kubernetes-specific deployment manifests.

Use GitHub Actions as the canonical CI/CD system. Workflows must run in GitHub-hosted CI and must also be runnable locally with `act`.

CI/CD checks should be exposed through shared local commands, preferably `make` targets, so GitHub Actions and local development use the same underlying commands. At minimum provide:

- `make lint`
- `make test`
- `make test-integration`
- `make scan`
- `make compose-check`
- `make ci`
- `make act-ci`

GitHub Actions workflows must call these shared commands rather than duplicating logic inline wherever practical.

Local workflow execution must be documented, including prerequisites for `act`, Docker, Docker Compose, and any required local secrets or environment files.

Production and staging deployment workflows must remain Docker Compose based. If orchestration assumptions are needed, model them with Compose files, Compose profiles, health checks, restart policies, and documented operational procedures.

## Core Requirements

Design and implement a unified Docker-based Python environment with:

- A single portable Python 3.11 slim-bullseye base image used by all services where appropriate.
- Django web framework service on port `8090` with a default scaffold.
- FastAPI web framework service on port `8099` with a default scaffold and async support.
- Caddy reverse proxy on ports `80` and `443` with routing rules and security features.
- PostgreSQL 15+ per service with connection pooling and replication for production-like environments.
- Redis Sentinel for high-availability caching and session storage in production-like environments.

## Dependency Management

Use `uv` for dependency management:

- Maintain `uv.lock` for deterministic builds.
- Use `uv python` for Python version management.
- Implement pre-build dependency vulnerability scanning.
- Optimize Docker layer caching with proper dependency ordering.

## Development-Focused Agent

Review and summarize the local development experience.

### Development Mode Architecture

For development mode only, use a simplified stack:

- Single PostgreSQL instance per service with no read replicas and no PGBouncer.
- Single Redis instance with no Sentinel cluster.
- Caddy with simple routing and no rate limiting.
- Full development images instead of distroless images.
- Debug tools included in development images.
- OpenTelemetry disabled by default or optional.
- No Argo Rollouts; use Docker Compose restart policies, health checks, and documented rollback procedures.

### Docker Compose Structure

Validate separate compose configurations:

- Base compose file with shared service definitions.
- Development compose file with simplified stack, volume mounts, and debug ports.
- Staging compose file with production-like environment.
- Staging and production must use Docker Compose overlays, not Kubernetes manifests.

### Dockerfile Targets

Validate a multi-stage Dockerfile with explicit targets:

- Development target with debug tools and hot-reload support.
- Builder target for dependency installation and optimization.
- Production target with distroless base and security hardening.

### Development Commands

Provide or validate commands for:

- Starting and stopping the development environment.
- Tailing logs for all services or specific services.
- Opening shells in service containers.
- Running unit, integration, and watch-mode tests.
- Resetting and seeding databases.
- Running migrations.
- Building and cleaning development images.
- Attaching debuggers.

### Hot Reload

Validate hot-reload configuration:
- Django reloader with volume mounts.
- File synchronization through Docker volume mounts.
- Automatic service restart on file changes.
- No rebuild required for ordinary code changes.

### Debugging

Validate debugging support:

- `debugpy` installed in development images.
- Debug ports exposed for each service.
- VS Code launch configuration provided.
- Breakpoint support in Django.
- Variable inspection support.
- Remote debugging support.
- Simultaneous debugging of multiple services.

### Development Logging

Validate development logging:

- Pretty human-readable console output with colors.
- `DEBUG` level enabled.
- Correlation IDs visible in console.
- SQL queries logged for debugging.
- Detailed request and response logging.
- Full stack traces displayed.

### Database Development Tools

Validate database tooling:

- Seed scripts for development data.
- Database reset commands.
- Factory Boy fixtures for consistent test data.
- Auto-apply migrations on startup.
- Django management commands.
- Direct database access on localhost ports.

### Development Testing

Validate developer-friendly testing:

- Auto-run tests on file changes.
- Quick test execution path that skips heavy tests.
- Isolated test databases through Testcontainers.
- Factory patterns for test data.
- Function-scoped fixtures.
- Fast unit test feedback loop.
- Parallel test execution.

### Environment Switching

Validate environment configuration:

- Configuration loader based on `ENV`.
- Separate environment files for development, staging, and production.
- Development mode as the default.
- Environment variable validation on startup.

### Development Resource Management

Validate productivity targets:

- Relaxed or removed container resource limits in development.
- Incremental builds target under 30 seconds.
- All services running within 30 seconds.
- Total memory usage under 4 GB.
- Minimal CPU usage at idle.

### Quality of Life

Validate developer experience:

- Service health status indicators.
- Port availability checks before startup.
- Dependency validation for Docker and Compose.
- Quick commands for common workflows.
- Log aggregation across services.
- Automatic cleanup on shutdown.

### Developer Onboarding

Validate onboarding documentation:

- Prerequisites.
- Clone and setup instructions.
- Service startup verification.
- Test execution guidance.
- Debugging setup instructions.
- Code modification workflow.

### Troubleshooting

Validate troubleshooting coverage:

- Port conflicts and resolution.
- Database connection issues.
- Hot-reload troubleshooting.
- Debugger attachment problems.
- Docker daemon issues.
- Permission errors.

### Development Security

Confirm development-only relaxed security:

- Plain environment variables with no Vault requirement.
- HTTP only with no SSL/TLS.
- Admin enabled with default credentials.
- CORS allowing all origins.
- No rate limiting.
- Relaxed OWASP headers.

## CI/CD-Focused Agent

Review and summarize pipeline, scanning, release, and deployment readiness.

Validate:

- Dependency installation through `uv`.
- Deterministic builds using `uv.lock`.
- Docker build cache optimization.
- Pre-build dependency vulnerability scanning.
- Container image vulnerability scanning.
- Secret scanning.
- Static analysis and linting.
- Unit, integration, and migration checks.
- Separate development, staging, and production workflows.
- Image tagging and provenance strategy.
- SBOM generation where appropriate.
- Deployment promotion must publish immutable image tags or digests and update Compose-based environment configuration.
- Rollback strategy must use the previous known-good image digest/tag with Docker Compose.
- Rollback strategy.
- Pipeline permissions using least privilege.
- Environment-specific configuration validation.
- Release artifacts and summaries that avoid raw log dumps.
- Remotely in GitHub CI/CD.
- Locally through `act`.

Validate that workflow jobs delegate to shared local commands such as `make ci`, `make test`, `make scan`, and `make compose-check`, so local and remote execution stay repeatable.

## Production-Focused Agent

Review and summarize production security, observability, reliability, and operations.

Validate:

- Production Docker target with minimal runtime surface.
- Distroless or hardened runtime image where compatible.
- Non-root container execution.
- Read-only filesystem where practical.
- Minimal Linux capabilities.
- Secure Caddy configuration for production.
- TLS configuration for production.
- Production OWASP headers.
- Rate limiting in production.
- CORS restricted to approved origins.
- PostgreSQL 15+ per service with connection pooling and replication.
- Redis Sentinel for high availability.
- Secrets management strategy.
- Backup and restore strategy.
- Migration strategy.
- Health checks and readiness checks.
- Structured JSON logs in production.
- Correlation IDs across services.
- Metrics and tracing with OpenTelemetry where appropriate.
- Alerting and runbook coverage.
- Operational dashboards.
- Compliance risks and validation requirements.


## After Execution

Each subagent returns a concise summary to the main thread. The main thread waits until all requested results are available, then returns a consolidated response.

The consolidated response must include:

- Overall architecture summary.
- Development-focused summary.
- CI/CD-focused summary.
- Production-focused summary.
- Cross-agent conflicts or trade-offs.
- Final recommendations.
- Remaining blockers or assumptions.

The final response must not include raw subagent output. It should synthesize the subagent summaries into a single actionable result.
