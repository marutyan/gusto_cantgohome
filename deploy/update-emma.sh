#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "run with sudo" >&2
  exit 1
fi

SOURCE_DIR=${1:-$(pwd)}
APP_ROOT=/opt/gusto-cantgohome
DATA_ROOT=/var/lib/gusto-cantgohome
DATABASE_PATH=$DATA_ROOT/gusto.sqlite3
RELEASE=$(git -C "$SOURCE_DIR" rev-parse HEAD)
RELEASE_DIR="$APP_ROOT/releases/$RELEASE"
PREVIOUS=$(readlink -f "$APP_ROOT/current" || true)
BACKUP_PATH=
DATABASE_MAY_HAVE_CHANGED=0

wait_for_health() {
  local name=$1
  local url=$2
  local service=$3

  for _ in $(seq 1 30); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is healthy"
      return 0
    fi
    sleep 1
  done

  echo "$name did not become healthy" >&2
  systemctl status "$service" --no-pager --full || true
  journalctl -u "$service" -n 120 --no-pager || true
  return 1
}

rollback_deployment() {
  local status=$?
  local rollback_ok=1
  trap - ERR
  set +e

  echo "deployment failed; starting coordinated rollback" >&2
  systemctl stop gusto-public.service gusto-admin.service >/dev/null 2>&1 || true

  if [[ $DATABASE_MAY_HAVE_CHANGED -eq 1 ]]; then
    if [[ -z "$BACKUP_PATH" || ! -f "$BACKUP_PATH" ]]; then
      echo "verified database snapshot is unavailable; refusing to restart services" >&2
      rollback_ok=0
    elif ! sudo -u gusto-cantgohome env PYTHONPATH="$RELEASE_DIR" \
      "$APP_ROOT/venv/bin/python" "$RELEASE_DIR/scripts/restore_database.py" \
      "$BACKUP_PATH" --db "$DATABASE_PATH"; then
      echo "database restore failed; refusing to restart services" >&2
      rollback_ok=0
    fi
  fi

  if [[ -z "$PREVIOUS" || ! -d "$PREVIOUS" ]]; then
    echo "previous release is unavailable; refusing to restart services" >&2
    rollback_ok=0
  elif [[ $rollback_ok -eq 1 ]]; then
    ln -sfn "$PREVIOUS" "$APP_ROOT/current"
    if ! systemctl restart gusto-public.service gusto-admin.service \
      || ! wait_for_health public http://127.0.0.1:8010/health gusto-public.service \
      || ! wait_for_health admin http://127.0.0.1:8011/health gusto-admin.service; then
      echo "previous release did not recover; services remain stopped" >&2
      rollback_ok=0
    fi
  fi

  if [[ $rollback_ok -eq 1 ]]; then
    systemctl start gusto-reconcile.timer >/dev/null 2>&1 || true
    echo "rollback completed using $BACKUP_PATH" >&2
  else
    systemctl stop gusto-public.service gusto-admin.service >/dev/null 2>&1 || true
    echo "rollback incomplete; manual recovery is required" >&2
  fi
  exit "$status"
}

if [[ ! -x "$APP_ROOT/venv/bin/python" ]]; then
  echo "application is not installed; run deploy/install-emma.sh first" >&2
  exit 1
fi

trap rollback_deployment ERR
systemctl stop gusto-reconcile.timer >/dev/null 2>&1 || true
systemctl stop gusto-public.service gusto-admin.service

rm -rf "$RELEASE_DIR"
install -d "$RELEASE_DIR"
tar --exclude=.git --exclude=.venv -C "$SOURCE_DIR" -cf - . | tar -C "$RELEASE_DIR" -xf -
chown -R gusto-cantgohome:gusto-cantgohome "$RELEASE_DIR"

BACKUP_PATH=$(
  sudo -u gusto-cantgohome env PYTHONPATH="$RELEASE_DIR" \
    "$APP_ROOT/venv/bin/python" "$RELEASE_DIR/scripts/backup_database.py" \
    --db "$DATABASE_PATH" \
    --output-dir "$DATA_ROOT/backups"
)
if [[ -z "$BACKUP_PATH" || ! -f "$BACKUP_PATH" ]]; then
  echo "verified database snapshot was not created" >&2
  false
fi

"$APP_ROOT/venv/bin/pip" install "$SOURCE_DIR"
DATABASE_MAY_HAVE_CHANGED=1
sudo -u gusto-cantgohome env PYTHONPATH="$RELEASE_DIR" \
  "$APP_ROOT/venv/bin/python" "$RELEASE_DIR/scripts/migrate.py" \
  --db "$DATABASE_PATH"
ln -sfn "$RELEASE_DIR" "$APP_ROOT/current"

install -m 0644 "$SOURCE_DIR/deploy/gusto-public.service" /etc/systemd/system/gusto-public.service
install -m 0644 "$SOURCE_DIR/deploy/gusto-admin.service" /etc/systemd/system/gusto-admin.service
install -m 0644 "$SOURCE_DIR/deploy/gusto-reconcile.service" /etc/systemd/system/gusto-reconcile.service
install -m 0644 "$SOURCE_DIR/deploy/gusto-reconcile.timer" /etc/systemd/system/gusto-reconcile.timer
systemctl daemon-reload
systemctl enable gusto-public.service gusto-admin.service gusto-reconcile.timer

systemctl restart gusto-public.service gusto-admin.service
wait_for_health public http://127.0.0.1:8010/health gusto-public.service
wait_for_health admin http://127.0.0.1:8011/health gusto-admin.service
systemctl enable --now gusto-reconcile.timer
systemctl start gusto-reconcile.service

trap - ERR
echo "deployed $RELEASE; verified database snapshot: $BACKUP_PATH"
