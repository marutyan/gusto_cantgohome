from __future__ import annotations

import argparse
from pathlib import Path

from app.persistence.snapshots import create_timestamped_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = create_timestamped_snapshot(args.db, args.output_dir)
    print(destination)


if __name__ == "__main__":
    main()
