"""Compatibility facade for admin game use cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.use_cases.admin_game import AdminGameUseCases


def get_admin_state(database_path: Path) -> dict[str, Any]:
    return AdminGameUseCases(database_path).get_state()


def update_menu(database_path: Path, menu_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    return AdminGameUseCases(database_path).update_menu(menu_id, changes)


def create_menu(database_path: Path, values: dict[str, Any]) -> dict[str, Any]:
    return AdminGameUseCases(database_path).create_menu(values)


__all__ = ["create_menu", "get_admin_state", "update_menu"]
