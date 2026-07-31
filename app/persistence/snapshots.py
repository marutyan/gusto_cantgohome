from __future__ import annotations

import os
import sqlite3
from collections.abc import Collection
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.persistence.connections import connect
from app.persistence.integrity import REQUIRED_TABLES, assert_database_integrity


def _temporary_path(destination: Path) -> Path:
    return destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")


def _fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _copy_database(source: Path, destination: Path) -> None:
    with (
        connect(source, read_only=True) as source_connection,
        sqlite3.connect(destination) as target_connection,
    ):
        source_connection.backup(target_connection)
        target_connection.execute("PRAGMA journal_mode = DELETE")
        target_connection.commit()


def create_verified_snapshot(
    database_path: Path,
    destination: Path,
    *,
    required_tables: Collection[str] = REQUIRED_TABLES,
) -> Path:
    source = Path(database_path)
    target = Path(destination)
    assert_database_integrity(source, required_tables=required_tables)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(target)

    temporary = _temporary_path(target)
    try:
        _copy_database(source, temporary)
        assert_database_integrity(temporary, required_tables=required_tables)
        _fsync_file(temporary)
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def create_timestamped_snapshot(
    database_path: Path,
    output_dir: Path,
    *,
    label: str = "backup",
    required_tables: Collection[str] = REQUIRED_TABLES,
) -> Path:
    source = Path(database_path)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    suffix = source.suffix or ".sqlite3"
    destination = Path(output_dir) / f"{source.stem}.{label}.{timestamp}{suffix}"
    return create_verified_snapshot(
        source,
        destination,
        required_tables=required_tables,
    )


def restore_verified_snapshot(
    snapshot_path: Path,
    database_path: Path,
    *,
    required_tables: Collection[str] = REQUIRED_TABLES,
) -> None:
    snapshot = Path(snapshot_path)
    destination = Path(database_path)
    assert_database_integrity(snapshot, required_tables=required_tables)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(destination)
    try:
        _copy_database(snapshot, temporary)
        assert_database_integrity(temporary, required_tables=required_tables)
        _fsync_file(temporary)
        os.replace(temporary, destination)
        for suffix in ("-wal", "-shm"):
            Path(f"{destination}{suffix}").unlink(missing_ok=True)
        _fsync_directory(destination.parent)
        assert_database_integrity(destination, required_tables=required_tables)
    finally:
        temporary.unlink(missing_ok=True)
