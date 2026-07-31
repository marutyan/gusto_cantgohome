# ADR 0001: SQLite safety boundary

## Status

Proposed in #22 as part of #21.

## Context

The application stores the shared game state in a single SQLite database on `emma`. Public guesses, admin corrections, ranking imports, migrations, and deployments can all write to the same file. A code rollback alone is insufficient after a schema or data migration because the previous release may not be compatible with the modified database.

The UI, HTTP API, existing schema, and current data must remain unchanged while the internal architecture is reorganized.

## Decision

All SQLite access is routed through `app.persistence`.

### Connection invariants

- Read paths use a SQLite `mode=ro` URI and `PRAGMA query_only = ON`.
- Write paths use an explicit transaction and roll back on every exception.
- Foreign-key enforcement and a five-second busy timeout are enabled for every connection.
- WAL mode remains enabled for writable application connections.

### Integrity invariants

A database or snapshot is accepted only when all of the following hold:

- `PRAGMA quick_check` returns exactly `ok`.
- `PRAGMA foreign_key_check` returns no rows.
- `schema_versions`, `categories`, `menus`, and `guesses` exist.

### Snapshot invariants

- Snapshots use SQLite's online backup API rather than copying the live database file.
- A snapshot is written to a temporary file in the destination directory.
- The temporary snapshot is integrity-checked and fsynced before an atomic rename.
- Timestamped snapshot names prevent a previous backup from being overwritten.
- Restore verifies both the source snapshot and the restored database.

### Migration invariants

- A file lock serializes migration attempts from the public and admin processes.
- Migration statements and the `schema_versions` update execute in one explicit transaction.
- A non-empty database receives a verified pre-migration snapshot before pending migrations run.
- The complete database is checked after migration.

### Deployment invariants

- Public and admin services stop before the deployment snapshot is created.
- Migration starts only after a verified snapshot exists.
- A failed migration or health check restores both the database snapshot and the previous release.
- If database restore or release restore fails, application services remain stopped. The system must not serve from a mixed code/data state.

## Consequences

### Merits

- Read-only operations cannot accidentally mutate the database.
- Backups are validated before being considered usable.
- Failed deployments return code and data to the same point in time.
- Future repository and use-case refactoring can rely on one persistence contract.

### Demerits

- Deployments include a short write outage while services are stopped and the snapshot is created.
- Migration locking and snapshot verification add operational complexity.
- Automatic recovery deliberately prefers downtime over serving with an uncertain database state.

## Non-goals

- Changing the current schema or migration SQL.
- Replacing SQLite.
- Changing the public or admin UI.
- Changing HTTP routes, status codes, or response payloads.
