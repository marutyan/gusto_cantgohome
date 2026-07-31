from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from app.repositories.records import AdminCategoryRecord, AdminMenuRecord, MenuRankRecord


class AdminGameRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_categories(self) -> list[AdminCategoryRecord]:
        rows = self._connection.execute(
            "SELECT id, name, display_order FROM categories ORDER BY display_order, name"
        ).fetchall()
        return [
            AdminCategoryRecord(
                category_id=int(row["id"]),
                name=str(row["name"]),
                display_order=int(row["display_order"]),
            )
            for row in rows
        ]

    def list_menus(self) -> list[AdminMenuRecord]:
        rows = self._connection.execute(
            """
            SELECT m.id, m.name, m.rank, m.display_order, m.is_active,
                   c.name AS category_name, g.guessed_at
            FROM menus m
            JOIN categories c ON c.id = m.category_id
            LEFT JOIN guesses g ON g.menu_id = m.id
            ORDER BY c.display_order, m.display_order, m.name
            """
        ).fetchall()
        return [
            AdminMenuRecord(
                menu_id=str(row["id"]),
                name=str(row["name"]),
                rank=int(row["rank"]),
                display_order=int(row["display_order"]),
                is_active=bool(row["is_active"]),
                category_name=str(row["category_name"]),
                guessed_at=row["guessed_at"],
            )
            for row in rows
        ]

    def get_menu_rank(self, menu_id: str) -> MenuRankRecord | None:
        row = self._connection.execute(
            "SELECT id, rank FROM menus WHERE id = ?",
            (menu_id,),
        ).fetchone()
        if row is None:
            return None
        return MenuRankRecord(menu_id=str(row["id"]), rank=int(row["rank"]))

    def get_menu_id_by_rank(self, rank: int) -> str | None:
        row = self._connection.execute(
            "SELECT id FROM menus WHERE rank = ?",
            (rank,),
        ).fetchone()
        return None if row is None else str(row["id"])

    def get_category_id(self, name: str) -> int | None:
        row = self._connection.execute(
            "SELECT id FROM categories WHERE name = ?",
            (name,),
        ).fetchone()
        return None if row is None else int(row["id"])

    def next_category_display_order(self) -> int:
        return int(
            self._connection.execute(
                "SELECT COALESCE(MAX(display_order), -1) + 1 FROM categories"
            ).fetchone()[0]
        )

    def insert_category(self, name: str, display_order: int) -> int:
        cursor = self._connection.execute(
            "INSERT INTO categories(name, display_order) VALUES (?, ?)",
            (name, display_order),
        )
        return int(cursor.lastrowid)

    def update_menu_rank(self, menu_id: str, rank: int) -> None:
        self._connection.execute(
            "UPDATE menus SET rank = ? WHERE id = ?",
            (rank, menu_id),
        )

    def update_menu_fields(
        self,
        menu_id: str,
        updates: Mapping[str, str | int],
    ) -> None:
        if not updates:
            return
        allowed_columns = {"name", "category_id", "display_order", "is_active"}
        unknown_columns = set(updates) - allowed_columns
        if unknown_columns:
            raise ValueError(f"unsupported menu columns: {sorted(unknown_columns)}")
        assignments = ", ".join(f"{column} = ?" for column in updates)
        self._connection.execute(
            f"UPDATE menus SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [*updates.values(), menu_id],
        )

    def insert_guess(self, menu_id: str, guessed_at: str) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO guesses(menu_id, guessed_at) VALUES (?, ?)",
            (menu_id, guessed_at),
        )

    def delete_guess(self, menu_id: str) -> None:
        self._connection.execute("DELETE FROM guesses WHERE menu_id = ?", (menu_id,))

    def rank_exists(self, rank: int) -> bool:
        return (
            self._connection.execute(
                "SELECT 1 FROM menus WHERE rank = ?",
                (rank,),
            ).fetchone()
            is not None
        )

    def insert_menu(
        self,
        *,
        menu_id: str,
        name: str,
        category_id: int,
        rank: int,
        display_order: int,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO menus(id, name, category_id, rank, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (menu_id, name, category_id, rank, display_order),
        )
