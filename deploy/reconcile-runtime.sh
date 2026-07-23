#!/usr/bin/env bash
set -euo pipefail

PUBLIC_HEALTH_URL=http://127.0.0.1:8010/health
ADMIN_HEALTH_URL=http://127.0.0.1:8011/health
PUBLIC_SERVICE=gusto-public.service
ADMIN_SERVICE=gusto-admin.service
APP_ROOT=/opt/gusto-cantgohome

wait_for_health() {
  local name=$1
  local url=$2
  local service=$3

  if curl -fsS "$url" >/dev/null 2>&1; then
    echo "$name is healthy"
    return 0
  fi

  echo "$name is unhealthy; restarting $service" >&2
  systemctl restart "$service"

  for _ in $(seq 1 30); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name recovered"
      return 0
    fi
    sleep 1
  done

  echo "$name did not recover" >&2
  systemctl status "$service" --no-pager --full || true
  journalctl -u "$service" -n 120 --no-pager || true
  return 1
}

wait_for_health public "$PUBLIC_HEALTH_URL" "$PUBLIC_SERVICE"
wait_for_health admin "$ADMIN_HEALTH_URL" "$ADMIN_SERVICE"

if ! systemctl is-active --quiet tailscaled.service; then
  echo "tailscaled is inactive; starting it" >&2
  systemctl start tailscaled.service
fi

for _ in $(seq 1 30); do
  if tailscale status >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! tailscale status >/dev/null 2>&1; then
  echo "tailscale did not become ready" >&2
  exit 1
fi

bash "$APP_ROOT/current/deploy/configure-funnel.sh"
