from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.database import read_connection, transaction


class MenuNotFoundError(ValueError):
    pass


class RankConflictError(ValueError):
    pass


def _summary(connection: sqlite3.Connection) -> dict[str, Any]:
    answered_count = connection.execute("SELECT COUNT(*) FROM guesses").fetchone()[0]
    total_count = connection.execute(
        "SELECT COUNT(*) FROM menus WHERE is_active = 1"
    ).fetchone()[0]
    hit_ranks = [
        row["rank"]
        for row in connection.execute(
            """
            SELECT m.rank
            FROM guesses g
            JOIN menus m ON m.id = g.menu_id
            WHERE m.rank <= 10 AND m.is_active = 1
            ORDER BY m.rank
            """
        ).fetchall()
    ]
    updated_at = connection.execute("SELECT MAX(guessed_at) FROM guesses").fetchone()[0]
    return {
        "top10HitCount": len(hit_ranks),
        "hitRanks": hit_ranks,
        "answeredCount": answered_count,
        "totalCount": total_count,
        "updatedAt": updated_at,
    }


def get_public_state(database_path: Path) -> dict[str, Any]:
    with read_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                c.id AS category_id,
                c.name AS category_name,
                c.display_order AS category_order,
                m.id,
                m.name,
                m.display_order,
                m.rank,
                g.guessed_at
            FROM categories c
            JOIN menus m ON m.category_id = c.id
            LEFT JOIN guesses g ON g.menu_id = m.id
            WHERE m.is_active = 1
            ORDER BY c.display_order, c.name, m.display_order, m.name
            """
        ).fetchall()
        categories: dict[int, dict[str, Any]] = {}
        for row in rows:
            category = categories.setdefault(
                row["category_id"],
                {"id": row["category_id"], "name": row["category_name"], "menus": []},
            )
            menu: dict[str, Any] = {
                "id": row["id"],
                "name": row["name"],
                "answered": row["guessed_at"] is not None,
            }
            if row["guessed_at"] is not None:
                menu["rank"] = row["rank"]
                menu["guessedAt"] = row["guessed_at"]
            category["menus"].append(menu)
        return {"summary": _summary(connection), "categories": list(categories.values())}


def submit_guesses(database_path: Path, menu_ids: list[str]) -> dict[str, Any]:
    with transaction(database_path, immediate=True) as connection:
        placeholders = ",".join("?" for _ in menu_ids)
        rows = connection.execute(
            f"""
            SELECT id, name, rank
            FROM menus
            WHERE is_active = 1 AND id IN ({placeholders})
            """,
            menu_ids,
        ).fetchall()
        by_id = {row["id"]: row for row in rows}
        missing = [menu_id for menu_id in menu_ids if menu_id not in by_id]
        if missing:
            raise MenuNotFoundError(f"unknown or inactive menu IDs: {', '.join(missing)}")

        now = datetime.now(UTC).isoformat()
        results: list[dict[str, Any]] = []
        for menu_id in menu_ids:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO guesses(menu_id, guessed_at) VALUES (?, ?)",
                (menu_id, now),
            )
            row = by_id[menu_id]
            results.append(
                {
                    "menuId": menu_id,
                    "menuName": row["name"],
                    "rank": row["rank"],
                    "isTop10": row["rank"] <= 10,
                    "newlyAnswered": cursor.rowcount == 1,
                }
            )
        summary = _summary(connection)
    return {"results": results, "summary": summary}


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
