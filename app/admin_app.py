from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import migrate
from app.settings import load_settings
from app.use_cases.admin_game import AdminGameUseCases
from app.use_cases.system import DatabaseHealthUseCase
from app.web.admin import create_admin_router

BASE_DIR = Path(__file__).resolve().parent


def create_admin_app(database_path: str | Path | None = None) -> FastAPI:
    settings = load_settings(database_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        migrate(settings.database_path)
        yield

    app = FastAPI(
        title="Gusto Top 10 Admin",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    game = AdminGameUseCases(settings.database_path)
    health = DatabaseHealthUseCase(settings.database_path)
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    app.state.settings = settings
    app.state.game_use_cases = game
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.include_router(
        create_admin_router(
            game=game,
            health=health,
            templates=templates,
        )
    )
    return app


app = create_admin_app()
