from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.domain.errors import MenuNotFoundError
from app.schemas import GuessRequest
from app.use_cases.public_game import PublicGameUseCases
from app.use_cases.system import DatabaseHealthUseCase


def create_public_router(
    *,
    game: PublicGameUseCases,
    health: DatabaseHealthUseCase,
    templates: Jinja2Templates,
    poll_interval_ms: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Response:
        return templates.TemplateResponse(
            request=request,
            name="public/index.html",
            context={"poll_interval_ms": poll_interval_ms},
        )

    @router.get("/health")
    def health_status() -> dict[str, str]:
        return health.get_status()

    @router.get("/api/state")
    def state() -> dict[str, Any]:
        return game.get_state()

    @router.post("/api/guesses")
    def guesses(payload: GuessRequest) -> dict[str, Any]:
        try:
            return game.submit_guesses(payload.menu_ids)
        except MenuNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
