# Deployment to emma

## Constraints

- Keep the existing Funnel on HTTPS port 443 unchanged.
- Use HTTPS port 8443 for this application.
- Public app: `127.0.0.1:8010`.
- Admin app: `127.0.0.1:8011`.

## 1. Install application

On emma, from a reviewed checkout:

```bash
sudo ./deploy/install-emma.sh "$PWD"
```

## Updating an existing installation

From a reviewed checkout:

```bash
sudo ./deploy/update-emma.sh "$PWD"
```

The script creates a SQLite backup, deploys by commit SHA, runs migrations, switches the `current` symlink, and restores the previous release if either health check fails.

## 2. Import the private ranking workbook

Transfer the workbook directly to emma. Do not commit it to Git.

Dry-run:

```bash
/opt/gusto-cantgohome/venv/bin/python scripts/import_rankings.py \
  /path/to/gusto_menu_popularity_ranking_2026-07-16.xlsx \
  --db /var/lib/gusto-cantgohome/gusto.sqlite3 \
  --expected-count 120 \
  --guessed '赤身ビーフステーキ（100g）' \
  --guessed '焼きアボカドとヤングコーンの赤身ステーキ重御膳' \
  --guessed 'ごろっと白桃とアールグレイのパフェ' \
  --guessed 'マルゲリータピザ'
```

After reviewing the output, add `--apply`. Restart both services and delete the transferred workbook after verifying the data.

## 3. Configure Funnel

```bash
./deploy/configure-funnel.sh
```

Expected URL:

```text
https://emma-ms-7e16.tailc8a18b.ts.net:8443/
```

The command uses `--bg`, so Tailscale persists the configuration across reboots.

## 4. Acceptance checks

```bash
systemctl status gusto-public gusto-admin --no-pager
sudo tailscale funnel status
curl -fsS http://127.0.0.1:8010/health
curl -fsS http://127.0.0.1:8011/health
curl -fsS https://emma-ms-7e16.tailc8a18b.ts.net:8443/health
curl -fsS https://emma-ms-7e16.tailc8a18b.ts.net/health
```

The final command verifies the existing port-443 service remains healthy.
