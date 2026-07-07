# Operations

Production operations are Docker Compose based. Images should be promoted by immutable tags or digests, not mutable tags.

## Validate Compose

```sh
make compose-check
```

## Production Build

```sh
make prod-build
```

## Production Start

```sh
make prod-up
make prod-smoke
```

## Rollback

Set `PREVIOUS_ENV_FILE` to an env file that points to previous known-good image tags or digests.

```sh
PREVIOUS_ENV_FILE=/path/to/previous.env make rollback
```

Rollback does not reverse database migrations automatically. Migration compatibility must be decided before release.
