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

The installer enables the public app, admin app, and the runtime reconciliation timer. It waits for both health endpoints before completing and configures Funnel 8443 without changing ports 443 or 8444.

## Updating an existing installation

From a reviewed checkout:

```bash
sudo ./deploy/update-emma.sh "$PWD"
```

The script creates a SQLite backup, deploys by commit SHA, runs migrations, switches the `current` symlink, installs the latest systemd units, and restores the previous release if either health check fails.

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

## 3. Automatic recovery

The following units are enabled:

- `gusto-public.service`: starts at boot and restarts whenever the process exits.
- `gusto-admin.service`: starts at boot and restarts whenever the process exits.
- `gusto-reconcile.timer`: runs 45-60 seconds after boot and every five minutes.
- `gusto-reconcile.service`: repairs unhealthy app services and restores Funnel 8443 when missing.

The reconciliation logic only manages HTTPS port 8443. Existing Funnel mappings on ports 443 and 8444 are not modified.

Manual verification:

```bash
systemctl is-enabled gusto-public gusto-admin gusto-reconcile.timer
systemctl status gusto-public gusto-admin gusto-reconcile.timer --no-pager
systemctl list-timers gusto-reconcile.timer --no-pager
sudo systemctl start gusto-reconcile.service
sudo journalctl -u gusto-reconcile.service -n 100 --no-pager
```

## 4. Configure Funnel manually

Normally the reconciliation service handles this automatically. To reconcile immediately:

```bash
./deploy/configure-funnel.sh
```

Expected URL:

```text
https://emma-ms-7e16.tailc8a18b.ts.net:8443/
```

The command uses `--bg`, so Tailscale persists the configuration across reboots. The timer also restores the mapping if it is unexpectedly missing.

## 5. Acceptance checks

```bash
systemctl status gusto-public gusto-admin gusto-reconcile.timer --no-pager
sudo tailscale funnel status
curl -fsS http://127.0.0.1:8010/health
curl -fsS http://127.0.0.1:8011/health
curl -fsS https://emma-ms-7e16.tailc8a18b.ts.net:8443/health
curl -fsS https://emma-ms-7e16.tailc8a18b.ts.net/health
```

The final command verifies the existing port-443 service remains healthy.
