from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.admin_app import create_admin_app
from app.public_app import create_public_app

ROOT = Path(__file__).resolve().parent.parent


def test_importing_asgi_apps_does_not_create_default_database(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", "import app.public_app; import app.admin_app"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "data/gusto.sqlite3").exists()


def test_public_lifespan_initializes_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "public.sqlite3"
    app = create_public_app(database_path)
    assert not database_path.exists()

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "database": "ok"}

    assert database_path.is_file()


def test_admin_lifespan_initializes_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "admin.sqlite3"
    app = create_admin_app(database_path)
    assert not database_path.exists()

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "database": "ok"}

    assert database_path.is_file()


def test_public_api_responses_remain_non_cacheable(database_path: Path) -> None:
    with TestClient(create_public_app(database_path)) as client:
        response = client.get("/api/state")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
