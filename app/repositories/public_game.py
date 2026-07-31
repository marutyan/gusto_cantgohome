from __future__ import annotations

import sqlite3

from app.repositories.records import GameSummaryRecord, GuessMenuRecord, PublicMenuRecord


class PublicGameRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_summary(self) -> GameSummaryRecord:
        answered_count = int(
            self._connection.execute("SELECT COUNT(*) FROM guesses").fetchone()[0]
        )
        total_count = int(
            self._connection.execute(
                "SELECT COUNT(*) FROM menus WHERE is_active = 1"
            ).fetchone()[0]
        )
        hit_ranks = tuple(
            int(row["rank"])
            for row in self._connection.execute(
                """
                SELECT m.rank
                FROM guesses g
                JOIN menus m ON m.id = g.menu_id
                WHERE m.rank <= 10 AND m.is_active = 1
                ORDER BY m.rank
                """
            ).fetchall()
        )
        updated_at = self._connection.execute(
            "SELECT MAX(guessed_at) FROM guesses"
        ).fetchone()[0]
        return GameSummaryRecord(
            answered_count=answered_count,
            total_count=total_count,
            hit_ranks=hit_ranks,
            updated_at=updated_at,
        )

    def list_public_menus(self) -> list[PublicMenuRecord]:
        rows = self._connection.execute(
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
        return [
            PublicMenuRecord(
                category_id=int(row["category_id"]),
                category_name=str(row["category_name"]),
                menu_id=str(row["id"]),
                name=str(row["name"]),
                rank=int(row["rank"]),
                guessed_at=row["guessed_at"],
            )
            for row in rows
        ]

    def get_active_menus(self, menu_ids: list[str]) -> dict[str, GuessMenuRecord]:
        placeholders = ",".join("?" for _ in menu_ids)
        rows = self._connection.execute(
            f"""
            SELECT id, name, rank
            FROM menus
            WHERE is_active = 1 AND id IN ({placeholders})
            """,
            menu_ids,
        ).fetchall()
        return {
            str(row["id"]): GuessMenuRecord(
                menu_id=str(row["id"]),
                name=str(row["name"]),
                rank=int(row["rank"]),
            )
            for row in rows
        }

    def insert_guess(self, menu_id: str, guessed_at: str) -> bool:
        cursor = self._connection.execute(
            "INSERT OR IGNORE INTO guesses(menu_id, guessed_at) VALUES (?, ?)",
            (menu_id, guessed_at),
        )
        return cursor.rowcount == 1
