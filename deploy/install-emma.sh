#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "run with sudo" >&2
  exit 1
fi

SOURCE_DIR=${1:-$(pwd)}
APP_ROOT=/opt/gusto-cantgohome
DATA_ROOT=/var/lib/gusto-cantgohome
CONFIG_ROOT=/etc/gusto-cantgohome
RELEASE=$(git -C "$SOURCE_DIR" rev-parse HEAD)
RELEASE_DIR="$APP_ROOT/releases/$RELEASE"

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

id gusto-cantgohome >/dev/null 2>&1 || useradd --system --home-dir "$APP_ROOT" --shell /usr/sbin/nologin gusto-cantgohome
install -d -o gusto-cantgohome -g gusto-cantgohome "$APP_ROOT/releases" "$DATA_ROOT/backups"
install -d -m 0755 "$CONFIG_ROOT"

python3 -m venv "$APP_ROOT/venv"
"$APP_ROOT/venv/bin/pip" install --upgrade pip
"$APP_ROOT/venv/bin/pip" install "$SOURCE_DIR"

rm -rf "$RELEASE_DIR"
install -d "$RELEASE_DIR"
tar --exclude=.git --exclude=.venv -C "$SOURCE_DIR" -cf - . | tar -C "$RELEASE_DIR" -xf -
ln -sfn "$RELEASE_DIR" "$APP_ROOT/current"
chown -R gusto-cantgohome:gusto-cantgohome "$APP_ROOT" "$DATA_ROOT"

cat > "$CONFIG_ROOT/app.env" <<ENV
GUSTO_DB_PATH=$DATA_ROOT/gusto.sqlite3
GUSTO_POLL_INTERVAL_MS=10000
ENV
chmod 0644 "$CONFIG_ROOT/app.env"

install -m 0644 "$SOURCE_DIR/deploy/gusto-public.service" /etc/systemd/system/gusto-public.service
install -m 0644 "$SOURCE_DIR/deploy/gusto-admin.service" /etc/systemd/system/gusto-admin.service
install -m 0644 "$SOURCE_DIR/deploy/gusto-reconcile.service" /etc/systemd/system/gusto-reconcile.service
install -m 0644 "$SOURCE_DIR/deploy/gusto-reconcile.timer" /etc/systemd/system/gusto-reconcile.timer

sudo -u gusto-cantgohome "$APP_ROOT/venv/bin/python" "$RELEASE_DIR/scripts/migrate.py" --db "$DATA_ROOT/gusto.sqlite3"
systemctl daemon-reload
systemctl enable --now gusto-public.service gusto-admin.service

wait_for_health public http://127.0.0.1:8010/health gusto-public.service
wait_for_health admin http://127.0.0.1:8011/health gusto-admin.service
systemctl enable --now gusto-reconcile.timer
systemctl start gusto-reconcile.service
