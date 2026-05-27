#!/usr/bin/env bash
# Einmaliges TLS-Setup via acme.sh (Let's Encrypt).
# Vorraussetzung: DNS für pflegeos.de / care.pflegeos.de / api.pflegeos.de
# zeigt bereits auf die VPS-IP.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v acme.sh >/dev/null 2>&1; then
  echo "Installing acme.sh…"
  curl https://get.acme.sh | sh -s email="$(whoami)@pflegeos.de"
  export PATH="$HOME/.acme.sh:$PATH"
fi

CERTS_DIR="$ROOT/infra/certs"
mkdir -p "$CERTS_DIR"

for DOMAIN in pflegeos.de care.pflegeos.de api.pflegeos.de; do
  mkdir -p "$CERTS_DIR/$DOMAIN"
  acme.sh --issue -d "$DOMAIN" --standalone \
    --fullchain-file "$CERTS_DIR/$DOMAIN/fullchain.pem" \
    --key-file       "$CERTS_DIR/$DOMAIN/privkey.pem"
done

echo "TLS-Zertifikate liegen in $CERTS_DIR/"
echo "Nginx reload nicht vergessen: docker compose exec nginx nginx -s reload"
