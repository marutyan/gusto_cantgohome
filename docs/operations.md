# Operations

## Database backup

```bash
sudo -u gusto-cantgohome /opt/gusto-cantgohome/venv/bin/python \
  /opt/gusto-cantgohome/current/scripts/backup_database.py \
  --db /var/lib/gusto-cantgohome/gusto.sqlite3 \
  --output-dir /var/lib/gusto-cantgohome/backups
```

## Admin screen

```bash
ssh -L 18011:127.0.0.1:8011 emma
```

Open `http://127.0.0.1:18011` and edit one menu at a time. There is no whole-game reset or bulk delete.

## Automatic recovery

Application processes use `Restart=always` with no systemd start-rate limit. The `gusto-reconcile.timer` checks runtime health after boot and every five minutes.

```bash
systemctl status gusto-public gusto-admin gusto-reconcile.timer --no-pager
systemctl list-timers gusto-reconcile.timer --no-pager
sudo systemctl start gusto-reconcile.service
sudo journalctl -u gusto-reconcile.service -n 100 --no-pager
```

The reconciliation service performs these operations only when needed:

1. Restart the public service if `127.0.0.1:8010/health` is unavailable.
2. Restart the admin service if `127.0.0.1:8011/health` is unavailable.
3. Start `tailscaled` if it is inactive.
4. Restore Funnel port 8443 if the mapping is absent.

It does not modify the existing Funnel mappings on ports 443 or 8444.

## Rollback

1. Back up the database.
2. Point `/opt/gusto-cantgohome/current` to the previous reviewed release.
3. Restart `gusto-public` and `gusto-admin`.
4. Run `sudo systemctl start gusto-reconcile.service`.
5. Run local and Funnel health checks.

Do not restore an older database unless a schema or data migration actually requires it.
