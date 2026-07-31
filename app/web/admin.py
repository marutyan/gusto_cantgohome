from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.domain.errors import MenuNotFoundError, RankConflictError
from app.schemas import AdminMenuCreate, AdminMenuUpdate
from app.use_cases.admin_game import AdminGameUseCases
from app.use_cases.system import DatabaseHealthUseCase


def create_admin_router(
    *,
    game: AdminGameUseCases,
    health: DatabaseHealthUseCase,
    templates: Jinja2Templates,
) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Response:
        return templates.TemplateResponse(request=request, name="admin/index.html")

    @router.get("/health")
    def health_status() -> dict[str, str]:
        return health.get_status()

    @router.get("/api/admin/state")
    def state() -> dict[str, Any]:
        return game.get_state()

    @router.patch("/api/admin/menus/{menu_id}")
    def patch_menu(menu_id: str, payload: AdminMenuUpdate) -> dict[str, Any]:
        try:
            return game.update_menu(menu_id, payload.model_dump(exclude_unset=True))
        except MenuNotFoundError as exc:
            raise HTTPException(status_code=404, detail="menu not found") from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/api/admin/menus", status_code=201)
    def post_menu(payload: AdminMenuCreate) -> dict[str, Any]:
        try:
            return game.create_menu(payload.model_dump())
        except RankConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
