from __future__ import annotations

import argparse
from pathlib import Path

from app.persistence.snapshots import restore_verified_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    restore_verified_snapshot(args.snapshot, args.db)
    print(args.db)


if __name__ == "__main__":
    main()
