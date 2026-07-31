from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USE_CASE_FILES = tuple((ROOT / "app/use_cases").glob("*.py"))
WEB_FILES = tuple((ROOT / "app/web").glob("*.py"))
APP_FILES = (ROOT / "app/public_app.py", ROOT / "app/admin_app.py")


def test_use_cases_do_not_depend_on_fastapi() -> None:
    for path in USE_CASE_FILES:
        content = path.read_text(encoding="utf-8")
        assert "fastapi" not in content.lower(), f"{path.name} depends on FastAPI"


def test_web_adapters_do_not_access_repositories_or_database() -> None:
    forbidden = ("app.repositories", "app.database", "app.persistence")
    for path in WEB_FILES:
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"{path.name} bypasses use cases: {token}"


def test_composition_roots_do_not_define_routes() -> None:
    for path in APP_FILES:
        content = path.read_text(encoding="utf-8")
        assert "@app.get" not in content
        assert "@app.post" not in content
        assert "@app.patch" not in content
