#!/usr/bin/env bash
# Install deploy/nginx-umet.conf as the host nginx config for UMET, test it,
# and reload. Restores the previous config if the test fails.
#   sudo bash deploy/apply-nginx-seo.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/nginx-umet.conf"
DEST=/etc/nginx/conf.d/umet.conf
BACKUP="/etc/nginx/conf.d/umet.conf.bak-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "$DEST" "$BACKUP"
cp "$SRC" "$DEST"
if nginx -t; then
  systemctl reload nginx
  echo "Applied. Previous config: $BACKUP"
else
  cp -p "$BACKUP" "$DEST"
  echo "nginx -t failed; previous config restored." >&2
  exit 1
fi
