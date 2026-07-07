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

## Development Commands
Provide or validate commands for:
- Starting/stopping the environment.
- Tailing logs (all services or specific services).
- Opening shells in service containers.
- Running unit, integration, and watch-mode tests.
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
