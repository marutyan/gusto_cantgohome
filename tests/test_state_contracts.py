from __future__ import annotations

from pathlib import Path

from app.services.admin_game import get_admin_state
from app.services.public_game import get_public_state


def test_public_state_contract(database_path: Path) -> None:
    assert get_public_state(database_path) == {
        "summary": {
            "top10HitCount": 0,
            "hitRanks": [],
            "answeredCount": 0,
            "totalCount": 3,
            "updatedAt": None,
        },
        "categories": [
            {
                "id": 1,
                "name": "ハンバーグ",
                "menus": [
                    {"id": "menu-a", "name": "メニューA", "answered": False},
                    {"id": "menu-b", "name": "メニューB", "answered": False},
                    {"id": "menu-c", "name": "メニューC", "answered": False},
                ],
            }
        ],
    }


def test_admin_state_contract(database_path: Path) -> None:
    assert get_admin_state(database_path) == {
        "categories": [{"id": 1, "name": "ハンバーグ", "display_order": 0}],
        "menus": [
            {
                "id": "menu-a",
                "name": "メニューA",
                "rank": 1,
                "display_order": 0,
                "is_active": True,
                "category_name": "ハンバーグ",
                "guessed_at": None,
                "answered": False,
            },
            {
                "id": "menu-b",
                "name": "メニューB",
                "rank": 7,
                "display_order": 1,
                "is_active": True,
                "category_name": "ハンバーグ",
                "guessed_at": None,
                "answered": False,
            },
            {
                "id": "menu-c",
                "name": "メニューC",
                "rank": 19,
                "display_order": 2,
                "is_active": True,
                "category_name": "ハンバーグ",
                "guessed_at": None,
                "answered": False,
            },
        ],
    }
