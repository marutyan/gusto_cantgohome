from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    poll_interval_ms: int = 10_000


def load_settings(database_path: str | Path | None = None) -> Settings:
    path = Path(database_path or os.environ.get("GUSTO_DB_PATH", "data/gusto.sqlite3"))
    interval = int(os.environ.get("GUSTO_POLL_INTERVAL_MS", "10000"))
    return Settings(database_path=path, poll_interval_ms=max(interval, 2_000))
