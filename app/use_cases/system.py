from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.database import check_database


@dataclass(frozen=True, slots=True)
class DatabaseHealthUseCase:
    database_path: Path

    def get_status(self) -> dict[str, str]:
        ok = check_database(self.database_path)
        return {
            "status": "ok" if ok else "error",
            "database": "ok" if ok else "error",
        }
