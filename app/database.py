from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MIGRATION_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def read_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction(database_path: Path, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def migrate(database_path: Path) -> None:
    with transaction(database_path, immediate=True) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_versions").fetchall()
        }
        for path in sorted(MIGRATION_DIR.glob("*.sql")):
            version = int(path.stem.split("_", 1)[0])
            if version in applied:
                continue
            connection.executescript(path.read_text(encoding="utf-8"))
            connection.execute("INSERT INTO schema_versions(version) VALUES (?)", (version,))


def check_database(database_path: Path) -> bool:
    try:
        with read_connection(database_path) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()[0]
        return result == "ok"
    except sqlite3.Error:
        return False
