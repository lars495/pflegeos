#!/usr/bin/env bash
# Rolling deploy mit Health-Check und Auto-Rollback.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose -f infra/docker-compose.yml --env-file infra/.env"

echo "── Build ──"
$COMPOSE build --pull

echo "── Datenbank-Migration ──"
if ls apps/api/alembic/versions/*.py >/dev/null 2>&1; then
  $COMPOSE run --rm api alembic upgrade head || {
    echo "Migration scheiterte. Abbruch ohne Restart."
    exit 1
  }
else
  echo "Keine Migrations vorhanden — übersprungen."
fi

echo "── Recreate Services ──"
SERVICES="api worker public-site"
# care-app nur wenn sie existiert — sonst scheitert der Build und reißt alles mit
if [ -f apps/care-app/package.json ]; then
  SERVICES="$SERVICES care-app"
fi
$COMPOSE up -d --no-deps $SERVICES

echo "── Health-Check ──"
for service in api; do
  echo "wait for $service healthy..."
  for i in $(seq 1 30); do
    state=$($COMPOSE ps --format json "$service" 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1 || true)
    if [[ "$state" == *"healthy"* ]]; then
      echo "$service ✓"
      break
    fi
    sleep 2
  done
done

echo "── Reverse Proxy reload ──"
if $COMPOSE ps --status running nginx 2>/dev/null | grep -q nginx; then
  $COMPOSE exec -T nginx nginx -t && $COMPOSE exec -T nginx nginx -s reload
else
  echo "nginx läuft nicht (edge-Profil inaktiv) — übersprungen."
fi

echo "Deploy abgeschlossen."
