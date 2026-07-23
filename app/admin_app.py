from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import check_database, migrate
from app.schemas import AdminMenuCreate, AdminMenuUpdate
from app.services.game import (
    MenuNotFoundError,
    RankConflictError,
    create_menu,
    get_admin_state,
    update_menu,
)
from app.settings import load_settings

BASE_DIR = Path(__file__).resolve().parent


def create_admin_app(database_path: str | Path | None = None) -> FastAPI:
    settings = load_settings(database_path)
    migrate(settings.database_path)
    app = FastAPI(title="Gusto Top 10 Admin", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):  # type: ignore[no-untyped-def]
        return templates.TemplateResponse(request=request, name="admin/index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        ok = check_database(settings.database_path)
        return {
            "status": "ok" if ok else "error",
            "database": "ok" if ok else "error",
        }

    @app.get("/api/admin/state")
    def state() -> dict:
        return get_admin_state(settings.database_path)

    @app.patch("/api/admin/menus/{menu_id}")
    def patch_menu(menu_id: str, payload: AdminMenuUpdate) -> dict:
        try:
            changes = payload.model_dump(exclude_unset=True)
            return update_menu(settings.database_path, menu_id, changes)
        except MenuNotFoundError as exc:
            raise HTTPException(status_code=404, detail="menu not found") from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/admin/menus", status_code=201)
    def post_menu(payload: AdminMenuCreate) -> dict:
        try:
            return create_menu(settings.database_path, payload.model_dump())
        except RankConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return app


app = create_admin_app()
