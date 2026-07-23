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

## Rollback

1. Back up the database.
2. Point `/opt/gusto-cantgohome/current` to the previous reviewed release.
3. Restart `gusto-public` and `gusto-admin`.
4. Run local and Funnel health checks.

Do not restore an older database unless a schema or data migration actually requires it.
