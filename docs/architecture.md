# Architecture

## Public path

`Tailscale Funnel :8443 -> 127.0.0.1:8010 -> FastAPI -> SQLite`

The public state endpoint returns ranks only for answered menus. Unanswered ranks remain in SQLite and are never embedded in HTML or JavaScript.

## Administration path

The admin service binds to `127.0.0.1:8011`. Open it through SSH forwarding:

```bash
ssh -L 18011:127.0.0.1:8011 emma
```

Then browse to `http://127.0.0.1:18011`.

## Data consistency

SQLite uses foreign keys, WAL mode, a five-second busy timeout, and `BEGIN IMMEDIATE` for writes. Batch guesses are validated and committed atomically.
