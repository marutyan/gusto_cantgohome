#!/usr/bin/env bash
set -euo pipefail

PUBLIC_TARGET=http://127.0.0.1:8010
PUBLIC_HEALTH_URL=$PUBLIC_TARGET/health

if [[ ${EUID} -eq 0 ]]; then
  TAILSCALE=(tailscale)
else
  TAILSCALE=(sudo tailscale)
fi

if ! curl -fsS "$PUBLIC_HEALTH_URL" >/dev/null; then
  echo "public application is not healthy on 127.0.0.1:8010" >&2
  exit 1
fi

status=$("${TAILSCALE[@]}" funnel status 2>/dev/null || true)
port_block=$(awk '
  /^https:\/\/[^ ]+:8443([[:space:]]|$)/ {
    in_block = 1
    print
    next
  }
  in_block && /^https:\/\// { exit }
  in_block { print }
' <<<"$status")

if [[ -n "$port_block" ]]; then
  if grep -Fq "proxy $PUBLIC_TARGET" <<<"$port_block"; then
    echo "Funnel on 8443 is already configured for this application."
    printf '%s\n' "$status"
    exit 0
  fi

  echo "port 8443 is already configured for another target; inspect before changing it" >&2
  printf '%s\n' "$port_block" >&2
  exit 1
fi

"${TAILSCALE[@]}" funnel --bg --yes --https=8443 "$PUBLIC_TARGET"
"${TAILSCALE[@]}" funnel status
