from __future__ import annotations

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = args.output_dir / f"gusto-{timestamp}.sqlite3"
    with sqlite3.connect(args.db) as source, sqlite3.connect(destination) as target:
        source.backup(target)
    print(destination)


if __name__ == "__main__":
    main()
