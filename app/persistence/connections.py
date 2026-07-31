from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT_MS = 5_000
CONNECTION_TIMEOUT_SECONDS = 5


def _read_only_uri(database_path: Path) -> str:
    return f"{database_path.resolve().as_uri()}?mode=ro"


def connect(database_path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    path = Path(database_path)
    if read_only:
        if not path.is_file():
            raise FileNotFoundError(path)
        connection = sqlite3.connect(
            _read_only_uri(path),
            uri=True,
            timeout=CONNECTION_TIMEOUT_SECONDS,
            isolation_level=None,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            path,
            timeout=CONNECTION_TIMEOUT_SECONDS,
            isolation_level=None,
        )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    if read_only:
        connection.execute("PRAGMA query_only = ON")
    else:
        connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def read_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path, read_only=True)
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
