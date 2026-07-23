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

sudo -u gusto-cantgohome "$APP_ROOT/venv/bin/python" "$RELEASE_DIR/scripts/migrate.py" --db "$DATA_ROOT/gusto.sqlite3"
systemctl daemon-reload
systemctl enable --now gusto-public.service gusto-admin.service
curl -fsS http://127.0.0.1:8010/health
curl -fsS http://127.0.0.1:8011/health
