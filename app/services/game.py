"""Backward-compatible facade for game service imports."""

from app.services.admin_game import create_menu, get_admin_state, update_menu
from app.services.errors import MenuNotFoundError, RankConflictError
from app.services.public_game import get_public_state, submit_guesses

__all__ = [
    "MenuNotFoundError",
    "RankConflictError",
    "create_menu",
    "get_admin_state",
    "get_public_state",
    "submit_guesses",
    "update_menu",
]
