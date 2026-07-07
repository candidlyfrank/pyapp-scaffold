# Monitoring

Production should emit JSON logs and include correlation IDs across both services. OpenTelemetry variables are present in env templates so traces and metrics can be routed to the selected backend.

Recommended dashboards:

- HTTP request rate, latency, and error rate.
- Container restarts and health check failures.
- PostgreSQL connections, replication lag, storage, and slow queries.
- Redis memory, command latency, and persistence status.
- Caddy status codes and TLS certificate expiry.

Recommended alerts:

- Any service unhealthy for more than five minutes.
- PostgreSQL unavailable or disk usage above threshold.
- Redis unavailable.
- Elevated 5xx response rate.
- TLS certificate expiry inside 14 days.
