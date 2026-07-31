from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICE_FILES = (
    ROOT / "app/services/public_game.py",
    ROOT / "app/services/admin_game.py",
)
REPOSITORY_FILES = (
    ROOT / "app/repositories/public_game.py",
    ROOT / "app/repositories/admin_game.py",
)


def test_services_do_not_embed_sql() -> None:
    forbidden = (".execute(", "SELECT ", "INSERT ", "UPDATE ", "DELETE ")
    for path in SERVICE_FILES:
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"{path.name} contains persistence detail: {token}"


def test_repositories_do_not_manage_transactions() -> None:
    forbidden = (".commit(", ".rollback(", "transaction(", "read_connection(")
    for path in REPOSITORY_FILES:
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"{path.name} manages connection lifetime: {token}"
