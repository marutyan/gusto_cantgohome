from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.database import read_connection, transaction
from app.services.errors import MenuNotFoundError, RankConflictError


def get_admin_state(database_path: Path) -> dict[str, Any]:
    with read_connection(database_path) as connection:
        categories = [
            dict(row)
            for row in connection.execute(
                "SELECT id, name, display_order FROM categories ORDER BY display_order, name"
            ).fetchall()
        ]
        menus = [
            {
                **dict(row),
                "is_active": bool(row["is_active"]),
                "answered": row["guessed_at"] is not None,
            }
            for row in connection.execute(
                """
                SELECT m.id, m.name, m.rank, m.display_order, m.is_active,
                       c.name AS category_name, g.guessed_at
                FROM menus m
                JOIN categories c ON c.id = m.category_id
                LEFT JOIN guesses g ON g.menu_id = m.id
                ORDER BY c.display_order, m.display_order, m.name
                """
            ).fetchall()
        ]
    return {"categories": categories, "menus": menus}


def _category_id(connection: sqlite3.Connection, category_name: str) -> int:
    normalized = category_name.strip()
    row = connection.execute(
        "SELECT id FROM categories WHERE name = ?", (normalized,)
    ).fetchone()
    if row:
        return row["id"]
    next_order = connection.execute(
        "SELECT COALESCE(MAX(display_order), -1) + 1 FROM categories"
    ).fetchone()[0]
    cursor = connection.execute(
        "INSERT INTO categories(name, display_order) VALUES (?, ?)",
        (normalized, next_order),
    )
    return int(cursor.lastrowid)


def update_menu(database_path: Path, menu_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    with transaction(database_path, immediate=True) as connection:
        current = connection.execute("SELECT * FROM menus WHERE id = ?", (menu_id,)).fetchone()
        if current is None:
            raise MenuNotFoundError(menu_id)

        updates: dict[str, Any] = {}
        if changes.get("name") is not None:
            updates["name"] = changes["name"].strip()
        if changes.get("category_name") is not None:
            updates["category_id"] = _category_id(connection, changes["category_name"])
        if changes.get("display_order") is not None:
            updates["display_order"] = changes["display_order"]
        if changes.get("is_active") is not None:
            updates["is_active"] = int(changes["is_active"])

        requested_rank = changes.get("rank")
        if requested_rank is not None and requested_rank != current["rank"]:
            occupied = connection.execute(
                "SELECT id FROM menus WHERE rank = ?", (requested_rank,)
            ).fetchone()
            temporary_rank = -int(current["rank"])
            connection.execute("UPDATE menus SET rank = ? WHERE id = ?", (temporary_rank, menu_id))
            if occupied:
                connection.execute(
                    "UPDATE menus SET rank = ? WHERE id = ?",
                    (current["rank"], occupied["id"]),
                )
            connection.execute("UPDATE menus SET rank = ? WHERE id = ?", (requested_rank, menu_id))

        if updates:
            assignments = ", ".join(f"{column} = ?" for column in updates)
            connection.execute(
                f"UPDATE menus SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [*updates.values(), menu_id],
            )

        answered = changes.get("answered")
        if answered is True:
            connection.execute(
                "INSERT OR IGNORE INTO guesses(menu_id, guessed_at) VALUES (?, ?)",
                (menu_id, datetime.now(UTC).isoformat()),
            )
        elif answered is False:
            connection.execute("DELETE FROM guesses WHERE menu_id = ?", (menu_id,))

    state = get_admin_state(database_path)
    return next(menu for menu in state["menus"] if menu["id"] == menu_id)


def create_menu(database_path: Path, values: dict[str, Any]) -> dict[str, Any]:
    menu_id = str(uuid4())
    with transaction(database_path, immediate=True) as connection:
        if connection.execute("SELECT 1 FROM menus WHERE rank = ?", (values["rank"],)).fetchone():
            raise RankConflictError(f"rank {values['rank']} is already used")
        category_id = _category_id(connection, values["category_name"])
        connection.execute(
            """
            INSERT INTO menus(id, name, category_id, rank, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                menu_id,
                values["name"].strip(),
                category_id,
                values["rank"],
                values["display_order"],
            ),
        )
        if values.get("answered"):
            connection.execute(
                "INSERT INTO guesses(menu_id, guessed_at) VALUES (?, ?)",
                (menu_id, datetime.now(UTC).isoformat()),
            )
    state = get_admin_state(database_path)
    return next(menu for menu in state["menus"] if menu["id"] == menu_id)
