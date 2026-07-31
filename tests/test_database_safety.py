from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.database import migrate, read_connection, transaction
from app.persistence import migrations
from app.persistence.integrity import DatabaseIntegrityError, assert_database_integrity
from app.persistence.snapshots import create_timestamped_snapshot, restore_verified_snapshot


def _database_dump(database_path: Path) -> dict[str, list[tuple[object, ...]]]:
    with read_connection(database_path) as connection:
        return {
            "schema_versions": [
                tuple(row)
                for row in connection.execute(
                    "SELECT version, applied_at FROM schema_versions ORDER BY version"
                )
            ],
            "categories": [
                tuple(row)
                for row in connection.execute(
                    "SELECT id, name, display_order FROM categories ORDER BY id"
                )
            ],
            "menus": [
                tuple(row)
                for row in connection.execute(
                    """
                    SELECT id, name, category_id, rank, display_order, is_active,
                           created_at, updated_at
                    FROM menus
                    ORDER BY id
                    """
                )
            ],
            "guesses": [
                tuple(row)
                for row in connection.execute(
                    "SELECT menu_id, guessed_at FROM guesses ORDER BY menu_id"
                )
            ],
        }


def test_read_connection_rejects_writes(database_path: Path) -> None:
    with (
        read_connection(database_path) as connection,
        pytest.raises(sqlite3.OperationalError, match="readonly"),
    ):
        connection.execute("DELETE FROM menus")


def test_transaction_rolls_back_all_changes(database_path: Path) -> None:
    before = _database_dump(database_path)
    with (
        pytest.raises(RuntimeError, match="abort"),
        transaction(database_path, immediate=True) as connection,
    ):
        connection.execute("DELETE FROM menus")
        raise RuntimeError("abort")
    assert _database_dump(database_path) == before


def test_snapshot_restore_round_trip_preserves_exact_rows(
    database_path: Path,
    tmp_path: Path,
) -> None:
    with transaction(database_path, immediate=True) as connection:
        connection.execute("INSERT INTO guesses(menu_id) VALUES ('menu-b')")
    before = _database_dump(database_path)
    snapshot = create_timestamped_snapshot(database_path, tmp_path / "backups")

    with transaction(database_path, immediate=True) as connection:
        connection.execute("DELETE FROM guesses")
        connection.execute("UPDATE menus SET name = '破壊後' WHERE id = 'menu-a'")

    restore_verified_snapshot(snapshot, database_path)
    assert _database_dump(database_path) == before
    assert_database_integrity(database_path)


def test_snapshots_never_overwrite_an_existing_backup(
    database_path: Path,
    tmp_path: Path,
) -> None:
    first = create_timestamped_snapshot(database_path, tmp_path / "backups")
    second = create_timestamped_snapshot(database_path, tmp_path / "backups")
    assert first != second
    assert first.is_file()
    assert second.is_file()


def test_corrupted_snapshot_is_rejected(tmp_path: Path) -> None:
    corrupted = tmp_path / "corrupted.sqlite3"
    corrupted.write_bytes(b"not a sqlite database")
    with pytest.raises(DatabaseIntegrityError):
        restore_verified_snapshot(corrupted, tmp_path / "target.sqlite3")


def test_failed_migration_rolls_back_schema_and_version(
    database_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    (migration_dir / "001_initial.sql").write_text(
        (migrations.MIGRATION_DIR / "001_initial.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (migration_dir / "002_failure.sql").write_text(
        """
        CREATE TABLE should_rollback (id INTEGER PRIMARY KEY);
        INSERT INTO table_that_does_not_exist(id) VALUES (1);
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(migrations, "MIGRATION_DIR", migration_dir)

    with pytest.raises(sqlite3.OperationalError):
        migrate(database_path)

    with read_connection(database_path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'should_rollback'"
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM schema_versions WHERE version = 2"
        ).fetchone() is None
    assert_database_integrity(database_path)
