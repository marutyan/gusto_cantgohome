from app.services import game
from app.services.admin_game import create_menu, get_admin_state, update_menu
from app.services.errors import MenuNotFoundError, RankConflictError
from app.services.public_game import get_public_state, submit_guesses


def test_game_module_preserves_existing_imports():
    assert game.MenuNotFoundError is MenuNotFoundError
    assert game.RankConflictError is RankConflictError
    assert game.create_menu is create_menu
    assert game.get_admin_state is get_admin_state
    assert game.get_public_state is get_public_state
    assert game.submit_guesses is submit_guesses
    assert game.update_menu is update_menu
