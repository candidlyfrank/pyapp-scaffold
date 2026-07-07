# Development-Focused Agent

Review and summarize the local development experience.

## Development Mode Architecture
For development mode only, use a simplified stack:
- Single PostgreSQL instance per service (no read replicas/PGBouncer).
- Single Redis instance (no Sentinel cluster).
- Caddy with simple routing and no rate limiting.
- Full development images instead of distroless images.
- Debug tools included in development images.
- OpenTelemetry disabled by default or optional.
- No Argo Rollouts; use Docker Compose restart policies, health checks, and documented rollback procedures.

## Docker Compose Structure
Validate separate compose configurations:
- Base compose file with shared service definitions.
- Development compose file with simplified stack, volume mounts, and debug ports.
- Staging compose file with production-like environment.
- Staging and production must use Docker Compose overlays.

## Dockerfile Targets
Validate a multi-stage Dockerfile with explicit targets:
- **Development target**: Debug tools and hot-reload support.
- **Builder target**: Dependency installation and optimization.
- **Production target**: Distroless base and security hardening.

## Python Project Isolation
Validate that Django and FastAPI are independent Python projects:
- Django must use `src/django/app` as its Python application package.
- FastAPI must use `src/fastapi/app` as its Python application package.
- Do not rename the Django package to `django_app`, `project`, `core`, or any
  other name.
- Do not rename the FastAPI package to `fastapi_app`, `project`, `core`, or any
  other name.
- Django owns `src/django/pyproject.toml` and `src/django/uv.lock`.
- FastAPI owns `src/fastapi/pyproject.toml` and `src/fastapi/uv.lock`.
- Django tests run with the Django project environment only.
- FastAPI tests run with the FastAPI project environment only.
- Django runtime dependencies do not include FastAPI-only packages.
- FastAPI runtime dependencies do not include Django-only packages.
- Root-level Python project files, if present, are limited to repository tooling
  and must not define either service's runtime dependency set.
- Dockerfiles install from service-local `pyproject.toml` and `uv.lock`, not
  from a shared root dependency lock.
- Ordinary local development commands must preserve service isolation while
  still offering a root-level `make` interface.
- Validation must fail if `src/django/django_app` or `src/fastapi/fastapi_app`
  exists, if Django settings reference `django_app.settings`, or if FastAPI
  commands reference `fastapi_app.main:app`.

## Development Commands
Provide or validate commands for:
- Starting/stopping the environment.
- Tailing logs (all services or specific services).
- Opening shells in service containers.
- Running unit, integration, and watch-mode tests.
- Running service-specific tests such as `make test-django` and
  `make test-fastapi` using each service's own `uv` project.
- Locking service dependencies independently, e.g. `make lock-django` and
  `make lock-fastapi`.
- Resetting/seeding databases and running migrations.
- Building/cleaning development images.
- Attaching debuggers.

## Hot Reload
Validate hot-reload configuration:
- Django reloader with volume mounts.
- File synchronization through Docker volume mounts.
- Automatic service restart on file changes.
- No rebuild required for ordinary code changes.

## Debugging
Validate debugging support:
- `debugpy` installed in development images.
- Debug ports exposed for each service.
- VS Code launch configuration provided.
- Breakpoint support (Django & remote).
- Simultaneous debugging of multiple services.

## Development Logging
Validate development logging:
- Pretty human-readable console output with colors.
- `DEBUG` level enabled.
- Correlation IDs visible in console.
- SQL queries logged for debugging.
- Detailed request and response logging.
- Full stack traces displayed.

## Database Development Tools
Validate database tooling:
- Seed scripts for development data.
- Database reset commands.
- Factory Boy fixtures for consistent test data.
- Auto-apply migrations on startup.
- Direct database access on localhost ports.

## Development Testing
Validate developer-friendly testing:
- Auto-run tests on file changes.
- Quick test execution path (skipping heavy tests).
- Isolated test databases via Testcontainers.
- Factory patterns for test data.
- Function-scoped fixtures and parallel execution.
- Service-local pytest configuration in each service's `pyproject.toml`.
- Root-level tests limited to repository contracts and cross-service integration.
- Test command execution must not rely on adding both `src/django` and
  `src/fastapi` to one shared root `pythonpath`; each service runs in its own
  project context so both can safely use an `app` package name.

## Environment Switching
Validate environment configuration:
- Configuration loader based on `ENV`.
- Separate environment files (dev, staging, prod).
- Development mode as the default.
- Environment variable validation on startup.

## Development Resource Management
Validate productivity targets:
- Relaxed/removed container resource limits.
- Incremental builds < 30s; Service startup < 30s.
- Total memory usage < 4 GB.
- Minimal CPU usage at idle.

## Quality of Life & Onboarding
- Service health status indicators.
- Port availability checks.
- Quick commands for common workflows.
- Log aggregation across services.
- Comprehensive documentation (Prerequisites, Setup, Startup, Debugging).

## Troubleshooting & Security
- Coverage for port conflicts, DB connections, and Docker/Daemon issues.
- **Dev Security (Relaxed):** Plain env vars, HTTP (no SSL/TLS), Admin/Default credentials, CORS allowing all origins, no rate limiting.
