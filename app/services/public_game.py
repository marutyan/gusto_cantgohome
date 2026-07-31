from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.database import read_connection, transaction
from app.repositories.public_game import PublicGameRepository
from app.services.errors import MenuNotFoundError


def _summary(repository: PublicGameRepository) -> dict[str, Any]:
    summary = repository.get_summary()
    return {
        "top10HitCount": len(summary.hit_ranks),
        "hitRanks": list(summary.hit_ranks),
        "answeredCount": summary.answered_count,
        "totalCount": summary.total_count,
        "updatedAt": summary.updated_at,
    }


def get_public_state(database_path: Path) -> dict[str, Any]:
    with read_connection(database_path) as connection:
        repository = PublicGameRepository(connection)
        categories: dict[int, dict[str, Any]] = {}
        for record in repository.list_public_menus():
            category = categories.setdefault(
                record.category_id,
                {"id": record.category_id, "name": record.category_name, "menus": []},
            )
            menu: dict[str, Any] = {
                "id": record.menu_id,
                "name": record.name,
                "answered": record.guessed_at is not None,
            }
            if record.guessed_at is not None:
                menu["rank"] = record.rank
                menu["guessedAt"] = record.guessed_at
            category["menus"].append(menu)
        return {"summary": _summary(repository), "categories": list(categories.values())}


def submit_guesses(database_path: Path, menu_ids: list[str]) -> dict[str, Any]:
    with transaction(database_path, immediate=True) as connection:
        repository = PublicGameRepository(connection)
        by_id = repository.get_active_menus(menu_ids)
        missing = [menu_id for menu_id in menu_ids if menu_id not in by_id]
        if missing:
            raise MenuNotFoundError(f"unknown or inactive menu IDs: {', '.join(missing)}")

        now = datetime.now(UTC).isoformat()
        results: list[dict[str, Any]] = []
        for menu_id in menu_ids:
            record = by_id[menu_id]
            results.append(
                {
                    "menuId": menu_id,
                    "menuName": record.name,
                    "rank": record.rank,
                    "isTop10": record.rank <= 10,
                    "newlyAnswered": repository.insert_guess(menu_id, now),
                }
            )
        summary = _summary(repository)
    return {"results": results, "summary": summary}
