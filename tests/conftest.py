from __future__ import annotations

from pathlib import Path

import pytest

from app.database import migrate, transaction


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    migrate(path)
    with transaction(path, immediate=True) as connection:
        category_id = connection.execute(
            "INSERT INTO categories(name, display_order) VALUES ('ハンバーグ', 0)"
        ).lastrowid
        connection.executemany(
            """
            INSERT INTO menus(id, name, category_id, rank, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("menu-a", "メニューA", category_id, 1, 0),
                ("menu-b", "メニューB", category_id, 7, 1),
                ("menu-c", "メニューC", category_id, 19, 2),
            ],
        )
    return path
