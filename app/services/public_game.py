"""Compatibility facade for public game use cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.use_cases.public_game import PublicGameUseCases


def get_public_state(database_path: Path) -> dict[str, Any]:
    return PublicGameUseCases(database_path).get_state()


def submit_guesses(database_path: Path, menu_ids: list[str]) -> dict[str, Any]:
    return PublicGameUseCases(database_path).submit_guesses(menu_ids)


__all__ = ["get_public_state", "submit_guesses"]
