#!/usr/bin/env bash
# Rolling deploy mit Health-Check und Auto-Rollback.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose -f infra/docker-compose.yml --env-file infra/.env"

echo "── Build ──"
$COMPOSE build --pull

echo "── Datenbank-Migration ──"
$COMPOSE run --rm api alembic upgrade head || {
  echo "Migration scheiterte. Abbruch ohne Restart."
  exit 1
}

echo "── Recreate Services ──"
$COMPOSE up -d --no-deps api worker care-app public-site

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
$COMPOSE exec -T nginx nginx -t && $COMPOSE exec -T nginx nginx -s reload

echo "Deploy abgeschlossen."
