from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.database import read_connection, transaction
from app.repositories.admin_game import AdminGameRepository
from app.services.errors import MenuNotFoundError, RankConflictError


def _category_id(repository: AdminGameRepository, category_name: str) -> int:
    normalized = category_name.strip()
    category_id = repository.get_category_id(normalized)
    if category_id is not None:
        return category_id
    return repository.insert_category(
        normalized,
        repository.next_category_display_order(),
    )


def get_admin_state(database_path: Path) -> dict[str, Any]:
    with read_connection(database_path) as connection:
        repository = AdminGameRepository(connection)
        categories = [
            {
                "id": record.category_id,
                "name": record.name,
                "display_order": record.display_order,
            }
            for record in repository.list_categories()
        ]
        menus = [
            {
                "id": record.menu_id,
                "name": record.name,
                "rank": record.rank,
                "display_order": record.display_order,
                "is_active": record.is_active,
                "category_name": record.category_name,
                "guessed_at": record.guessed_at,
                "answered": record.guessed_at is not None,
            }
            for record in repository.list_menus()
        ]
    return {"categories": categories, "menus": menus}


def update_menu(database_path: Path, menu_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    with transaction(database_path, immediate=True) as connection:
        repository = AdminGameRepository(connection)
        current = repository.get_menu_rank(menu_id)
        if current is None:
            raise MenuNotFoundError(menu_id)

        updates: dict[str, str | int] = {}
        if changes.get("name") is not None:
            updates["name"] = changes["name"].strip()
        if changes.get("category_name") is not None:
            updates["category_id"] = _category_id(repository, changes["category_name"])
        if changes.get("display_order") is not None:
            updates["display_order"] = changes["display_order"]
        if changes.get("is_active") is not None:
            updates["is_active"] = int(changes["is_active"])

        requested_rank = changes.get("rank")
        if requested_rank is not None and requested_rank != current.rank:
            occupied_menu_id = repository.get_menu_id_by_rank(requested_rank)
            repository.update_menu_rank(menu_id, -current.rank)
            if occupied_menu_id is not None:
                repository.update_menu_rank(occupied_menu_id, current.rank)
            repository.update_menu_rank(menu_id, requested_rank)

        repository.update_menu_fields(menu_id, updates)

        answered = changes.get("answered")
        if answered is True:
            repository.insert_guess(menu_id, datetime.now(UTC).isoformat())
        elif answered is False:
            repository.delete_guess(menu_id)

    state = get_admin_state(database_path)
    return next(menu for menu in state["menus"] if menu["id"] == menu_id)


def create_menu(database_path: Path, values: dict[str, Any]) -> dict[str, Any]:
    menu_id = str(uuid4())
    with transaction(database_path, immediate=True) as connection:
        repository = AdminGameRepository(connection)
        if repository.rank_exists(values["rank"]):
            raise RankConflictError(f"rank {values['rank']} is already used")
        category_id = _category_id(repository, values["category_name"])
        repository.insert_menu(
            menu_id=menu_id,
            name=values["name"].strip(),
            category_id=category_id,
            rank=values["rank"],
            display_order=values["display_order"],
        )
        if values.get("answered"):
            repository.insert_guess(menu_id, datetime.now(UTC).isoformat())
    state = get_admin_state(database_path)
    return next(menu for menu in state["menus"] if menu["id"] == menu_id)
