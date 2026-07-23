from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.database import read_connection, transaction


class MenuNotFoundError(ValueError):
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
