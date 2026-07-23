# gusto_cantgohome

A small shared web application for guessing Gusto's top-10 menu ranking. The public UI reveals a rank only after a menu is submitted. The game state is shared through SQLite on `emma` and published through Tailscale Funnel.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python scripts/migrate.py --db data/gusto.sqlite3
uvicorn app.public_app:app --reload --port 8010
```

Admin UI:

```bash
GUSTO_DB_PATH=data/gusto.sqlite3 uvicorn app.admin_app:app --reload --port 8011
```

## Validation

```bash
ruff check .
pytest
```

## Data handling

Ranking workbooks, CSV files, SQLite databases, backups, credentials, and `.env` files must not be committed. Import the private ranking file directly on emma with `scripts/import_rankings.py`.

## GitHub workflow

- Issue first.
- One issue is one outcome or decision unit.
- One commit is one logical unit.
- One pull request is one outcome.
- Preserve individual commits: do not squash merge.
- Do not merge without explicit approval.

See `docs/architecture.md`, `docs/deployment.md`, and `docs/operations.md`.
