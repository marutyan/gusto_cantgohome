from __future__ import annotations

import sqlite3
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.persistence.connections import read_connection

REQUIRED_TABLES = frozenset({"schema_versions", "categories", "menus", "guesses"})


@dataclass(frozen=True)
class IntegrityReport:
    quick_check: tuple[str, ...]
    foreign_key_violations: tuple[tuple[Any, ...], ...]
    missing_tables: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return (
            self.quick_check == ("ok",)
            and not self.foreign_key_violations
            and not self.missing_tables
        )

    def describe(self) -> str:
        parts: list[str] = []
        if self.quick_check != ("ok",):
            parts.append(f"quick_check={self.quick_check!r}")
        if self.foreign_key_violations:
            parts.append(f"foreign_key_violations={self.foreign_key_violations!r}")
        if self.missing_tables:
            parts.append(f"missing_tables={self.missing_tables!r}")
        return "; ".join(parts) or "ok"


class DatabaseIntegrityError(RuntimeError):
    pass


def inspect_database(
    database_path: Path,
    *,
    required_tables: Collection[str] = REQUIRED_TABLES,
) -> IntegrityReport:
    with read_connection(database_path) as connection:
        quick_check = tuple(
            str(row[0]) for row in connection.execute("PRAGMA quick_check").fetchall()
        )
        foreign_key_violations = tuple(
            tuple(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        existing_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    missing_tables = tuple(sorted(set(required_tables) - existing_tables))
    return IntegrityReport(
        quick_check=quick_check,
        foreign_key_violations=foreign_key_violations,
        missing_tables=missing_tables,
    )


def assert_database_integrity(
    database_path: Path,
    *,
    required_tables: Collection[str] = REQUIRED_TABLES,
) -> None:
    try:
        report = inspect_database(database_path, required_tables=required_tables)
    except (FileNotFoundError, OSError, sqlite3.Error) as exc:
        raise DatabaseIntegrityError(f"database cannot be inspected: {database_path}") from exc
    if not report.is_valid:
        raise DatabaseIntegrityError(report.describe())


def check_database(database_path: Path) -> bool:
    try:
        assert_database_integrity(database_path)
    except DatabaseIntegrityError:
        return False
    return True
