#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "run with sudo" >&2
  exit 1
fi

SOURCE_DIR=${1:-$(pwd)}
APP_ROOT=/opt/gusto-cantgohome
DATA_ROOT=/var/lib/gusto-cantgohome
RELEASE=$(git -C "$SOURCE_DIR" rev-parse HEAD)
RELEASE_DIR="$APP_ROOT/releases/$RELEASE"
PREVIOUS=$(readlink -f "$APP_ROOT/current" || true)

if [[ ! -x "$APP_ROOT/venv/bin/python" ]]; then
  echo "application is not installed; run deploy/install-emma.sh first" >&2
  exit 1
fi

sudo -u gusto-cantgohome "$APP_ROOT/venv/bin/python" \
  "$APP_ROOT/current/scripts/backup_database.py" \
  --db "$DATA_ROOT/gusto.sqlite3" \
  --output-dir "$DATA_ROOT/backups"

rm -rf "$RELEASE_DIR"
install -d "$RELEASE_DIR"
tar --exclude=.git --exclude=.venv -C "$SOURCE_DIR" -cf - . | tar -C "$RELEASE_DIR" -xf -
chown -R gusto-cantgohome:gusto-cantgohome "$RELEASE_DIR"

"$APP_ROOT/venv/bin/pip" install "$SOURCE_DIR"
sudo -u gusto-cantgohome "$APP_ROOT/venv/bin/python" \
  "$RELEASE_DIR/scripts/migrate.py" \
  --db "$DATA_ROOT/gusto.sqlite3"
ln -sfn "$RELEASE_DIR" "$APP_ROOT/current"

if ! systemctl restart gusto-public.service gusto-admin.service \
  || ! curl -fsS http://127.0.0.1:8010/health \
  || ! curl -fsS http://127.0.0.1:8011/health; then
  echo "deployment failed; restoring previous release" >&2
  if [[ -n "$PREVIOUS" && -d "$PREVIOUS" ]]; then
    ln -sfn "$PREVIOUS" "$APP_ROOT/current"
    systemctl restart gusto-public.service gusto-admin.service
  fi
  exit 1
fi

echo "deployed $RELEASE"
