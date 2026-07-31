from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import migrate
from app.settings import load_settings
from app.use_cases.public_game import PublicGameUseCases
from app.use_cases.system import DatabaseHealthUseCase
from app.web.middleware import no_store_api
from app.web.public import create_public_router

BASE_DIR = Path(__file__).resolve().parent


def create_public_app(database_path: str | Path | None = None) -> FastAPI:
    settings = load_settings(database_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        migrate(settings.database_path)
        yield

    app = FastAPI(
        title="Gusto Top 10 Challenge",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    game = PublicGameUseCases(settings.database_path)
    health = DatabaseHealthUseCase(settings.database_path)
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    app.state.settings = settings
    app.state.game_use_cases = game
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.middleware("http")(no_store_api)
    app.include_router(
        create_public_router(
            game=game,
            health=health,
            templates=templates,
            poll_interval_ms=settings.poll_interval_ms,
        )
    )
    return app


app = create_public_app()
