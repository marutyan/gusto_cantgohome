#!/usr/bin/env bash
set -euo pipefail

if ! curl -fsS http://127.0.0.1:8010/health >/dev/null; then
  echo "public application is not healthy on 127.0.0.1:8010" >&2
  exit 1
fi

status=$(sudo tailscale funnel status 2>/dev/null || true)
if grep -qE 'https://[^ ]+:8443' <<<"$status"; then
  if grep -q 'proxy http://127.0.0.1:8010' <<<"$status"; then
    echo "Funnel on 8443 is already configured for this application."
    printf '%s\n' "$status"
    exit 0
  fi
  echo "port 8443 is already configured for another target; inspect before changing it" >&2
  printf '%s\n' "$status" >&2
  exit 1
fi

sudo tailscale funnel --bg --yes --https=8443 http://127.0.0.1:8010
sudo tailscale funnel status
