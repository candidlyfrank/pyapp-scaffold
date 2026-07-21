# Deployment

The CI/CD model builds immutable service images, records SBOM/provenance, validates Compose configuration, and hands off deployment to a Docker Compose host or deployment runner.

## Promotion

1. Publish Django, FastAPI, and frontend images from a tag or protected release workflow.
2. Record image tags or digests in the target environment file.
3. Run `make compose-check`.
4. Apply the target Compose overlay.
5. Run smoke checks.

Set `FRONTEND_IMAGE` to an immutable image tag or digest alongside `DJANGO_IMAGE` and `FASTAPI_IMAGE`. The production frontend image must be built from the `production` Dockerfile target. Do not publish frontend or application service ports; only Caddy exposes ports `80` and `443`.

## Required Secrets

- Registry access through GitHub `GITHUB_TOKEN` for GHCR.
- Production env file or secret manager.
- TLS/ACME configuration for Caddy.

The public origin must also be listed in `DJANGO_CSRF_TRUSTED_ORIGINS`, and the public hostname must be listed in `DJANGO_ALLOWED_HOSTS`. `DJANGO_INTERNAL_URL` stays fixed to the private Compose address and is never exposed through a `NEXT_PUBLIC_*` variable.
