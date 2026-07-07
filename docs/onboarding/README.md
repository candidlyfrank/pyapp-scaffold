# Onboarding

## First Run

```sh
uv sync --locked --group dev
make up
```

Use `make logs SERVICE=django` or `make logs SERVICE=fastapi` to follow one service. Use `make shell SERVICE=django` to open a shell.

## Debugging

Start a debug target:

```sh
make debug-django
make debug-fastapi
```

Then attach from VS Code using `.vscode/launch.json`.

## Common Issues

- Port `80`, `443`, `8090`, `8099`, `5678`, `5679`, `5433`, `5434`, or `6379` already in use: stop the conflicting local service or change the mapped port in `docker-compose.dev.yml`.
- Docker daemon unavailable: start Docker Desktop or your Docker service.
- Database state is stale: run `make reset-db`.
