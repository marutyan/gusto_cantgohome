from __future__ import annotations

from fastapi import FastAPI

from app.database import check_database
from app.settings import Settings, load_settings


def create_public_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or load_settings()
    app = FastAPI(title="Gusto Can't Go Home")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "database": "ok" if check_database(resolved.database_path) else "error",
        }

    return app


app = create_public_app()
