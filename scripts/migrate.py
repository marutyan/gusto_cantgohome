from __future__ import annotations

import argparse
from pathlib import Path

from app.database import migrate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    migrate(args.db)
    print(f"migrated: {args.db}")


if __name__ == "__main__":
    main()
