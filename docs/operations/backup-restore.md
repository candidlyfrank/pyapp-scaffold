# Backup And Restore

## Backup

Use `pg_dump` or the managed database backup system for each PostgreSQL database. Store artifacts in encrypted storage with access logging.

```sh
make backup
```

## Restore

Restores require an explicit target environment, backup artifact, and approval. Test restores in staging before production use.

```sh
make restore
```

## RPO/RTO

RPO and RTO are deployment decisions and must be recorded before production launch.
