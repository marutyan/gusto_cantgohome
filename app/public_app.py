from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from app.database import check_database, migrate
from app.schemas import GuessRequest
from app.services.game import MenuNotFoundError, get_public_state, submit_guesses
from app.settings import load_settings


def create_public_app(database_path: str | Path | None = None) -> FastAPI:
    settings = load_settings(database_path)
    migrate(settings.database_path)
    app = FastAPI(title="Gusto Top 10 Challenge", docs_url=None, redoc_url=None)
    app.state.settings = settings

    @app.middleware("http")
    async def no_store_api(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        ok = check_database(settings.database_path)
        return {"status": "ok" if ok else "error", "database": "ok" if ok else "error"}

    @app.get("/api/state")
    def state() -> dict:
        return get_public_state(settings.database_path)

    @app.post("/api/guesses")
    def guesses(payload: GuessRequest) -> dict:
        try:
            return submit_guesses(settings.database_path, payload.menu_ids)
        except MenuNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_public_app()
