# Production-Focused Agent

Review and summarize production security, observability, reliability, and operations.

## Security and Hardening
- **Container Image**: Production Docker target with minimal runtime surface; Distroless or hardened base.
- **Execution Environment**:
    - Non-root container execution.
    - Read-only filesystem where practical.
    - Minimal Linux capabilities.
- **Network/Traffic**:
    - Secure Caddy configuration.
    - TLS configuration for production.
    - Production OWASP headers.
    - Rate limiting in production.
    - CORS restricted to approved origins.
- **Secrets**: Secure secrets management strategy.

## Production Dependency Isolation
Validate that production images preserve Django/FastAPI project independence:
- Django production images must copy and run the package at `src/django/app`.
- FastAPI production images must copy and run the package at `src/fastapi/app`.
- Production validation must fail if image commands reference
  `django_app.settings` or `fastapi_app.main:app`.
- Django production images install only from `src/django/pyproject.toml` and
  `src/django/uv.lock`.
- FastAPI production images install only from `src/fastapi/pyproject.toml` and
  `src/fastapi/uv.lock`.
- Production images do not include the other service's source code or runtime
  dependencies.
- SBOMs, vulnerability scans, and provenance must be generated per service image
  so dependency risk can be attributed to Django or FastAPI independently.
- Rollback and promotion must track separate immutable image references for
  Django and FastAPI.

## Reliability and Scaling
- **Database**: PostgreSQL 15+ per service with connection pooling and replication.
- **High Availability**: Redis Sentinel for high availability.
- **Deployment Operations**:
    - Health and readiness checks.
    - Backup and restore strategy.
    - Migration strategy.

## Observability and Operations
- **Logging**: Structured JSON logs in production.
- **Tracing**: Correlation IDs across services; OpenTelemetry for metrics and tracing.
- **Monitoring**:
    - Alerting and runbook coverage.
    - Operational dashboards.
- **Compliance**: Assessment of compliance risks and validation requirements.
