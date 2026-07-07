# Deployment

The CI/CD model builds immutable service images, records SBOM/provenance, validates Compose configuration, and hands off deployment to a Docker Compose host or deployment runner.

## Promotion

1. Publish Django and FastAPI images from a tag or protected release workflow.
2. Record image tags or digests in the target environment file.
3. Run `make compose-check`.
4. Apply the target Compose overlay.
5. Run smoke checks.

## Required Secrets

- Registry access through GitHub `GITHUB_TOKEN` for GHCR.
- Production env file or secret manager.
- TLS/ACME configuration for Caddy.
