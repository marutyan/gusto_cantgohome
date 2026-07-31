from __future__ import annotations

import fcntl
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.persistence.connections import connect, transaction
from app.persistence.integrity import assert_database_integrity
from app.persistence.snapshots import create_timestamped_snapshot

MIGRATION_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


@contextmanager
def _migration_lock(database_path: Path) -> Iterator[None]:
    lock_path = database_path.with_name(f"{database_path.name}.migration.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _migration_paths() -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    versions: set[int] = set()
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        version = int(path.stem.split("_", 1)[0])
        if version in versions:
            raise ValueError(f"duplicate migration version: {version}")
        versions.add(version)
        migrations.append((version, path))
    return migrations


def _applied_versions(database_path: Path) -> set[int]:
    if not database_path.is_file() or database_path.stat().st_size == 0:
        return set()
    with connect(database_path, read_only=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_versions'"
        ).fetchone()
        if not exists:
            return set()
        return {
            int(row[0]) for row in connection.execute("SELECT version FROM schema_versions")
        }


def _contains_sql(script: str) -> bool:
    return any(
        line.strip() and not line.lstrip().startswith("--")
        for line in script.splitlines()
    )


def _statements(script: str) -> Iterator[str]:
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if _contains_sql(statement):
                yield statement
            buffer = ""
    if _contains_sql(buffer):
        raise ValueError("migration contains an incomplete SQL statement")


def migrate(database_path: Path) -> None:
    path = Path(database_path)
    with _migration_lock(path):
        migrations = _migration_paths()
        applied = _applied_versions(path)
        pending = [(version, file) for version, file in migrations if version not in applied]
        if pending and path.is_file() and path.stat().st_size:
            create_timestamped_snapshot(
                path,
                path.parent / "backups",
                label=f"before-migration-{pending[0][0]}-{pending[-1][0]}",
                required_tables=(),
            )

        with transaction(path, immediate=True) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            applied_in_transaction = {
                int(row[0])
                for row in connection.execute("SELECT version FROM schema_versions")
            }
            for version, migration_path in migrations:
                if version in applied_in_transaction:
                    continue
                for statement in _statements(migration_path.read_text(encoding="utf-8")):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_versions(version) VALUES (?)",
                    (version,),
                )
        assert_database_integrity(path)
