#!/usr/bin/env bash
# Täglicher Build-Cycle für PflegeOS.
#
# Cron: 0 3 * * * cd /home/pflegeos/pflegeos && ./scripts/daily_agent.sh >> logs/daily.log 2>&1
#
# Voraussetzungen:
#   - Repo-Wurzel als CWD
#   - infra/.env existiert
#   - Docker Compose Stack läuft (`make up`)
#   - claude oder hermes CLI installiert und konfiguriert
#
# Verhalten:
#   1. Pull latest main (falls jemand manuell gepusht hat)
#   2. Community-Contributions verarbeiten
#   3. Build-Agent starten (mit AGENT_INSTRUCTIONS.md als Prompt)
#   4. Tests laufen lassen
#   5. Bei grün: deployen
#   6. Daily-Report generieren
#   7. Update posten

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATE=$(date +%Y-%m-%d)
LOG_DIR="$ROOT/logs"
REPORT_FILE="$ROOT/reports/daily/$DATE.md"

mkdir -p "$LOG_DIR" "$(dirname "$REPORT_FILE")"

# Heartbeat-Datei für Monitoring
echo "$(date -Iseconds) starting daily agent" >> "$LOG_DIR/heartbeat.log"

# ─── Budget-Status-Check ─────────────────────────────────────
echo "── Budget vor Lauf ──"
make budget || true

# ─── 1. Code aktualisieren ───────────────────────────────────
git fetch origin main
LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse origin/main)
if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
  echo "Pulling new commits from origin/main"
  git pull --ff-only origin main
fi

# ─── 2. Community-Beiträge ───────────────────────────────────
echo "── Community-Beiträge verarbeiten ──"
make process-contributions || echo "process-contributions failed (continuing)"

# ─── 3. Build-Agent ──────────────────────────────────────────
echo "── Build-Agent ($DATE) ──"

# .env in die aktuelle Shell laden (für REDIS_URL, OPENROUTER_API_KEY)
set -a
source infra/.env
set +a
export REDIS_URL="redis://:${REDIS_PASSWORD}@127.0.0.1:6379/0"

# Python-Agent läuft auf dem Host (braucht git-Zugriff fürs Commit/Push)
python3 scripts/build_agent.py 2>&1 | tee "$LOG_DIR/agent-$DATE.log"
AGENT_EXIT=${PIPESTATUS[0]}
echo "[daily_agent] build_agent exit: $AGENT_EXIT"

# ─── 4. Tests + Deploy (nur falls Agent etwas committed hat) ──
if [[ "$AGENT_EXIT" -eq 0 ]]; then
  echo "── Tests im API-Container ──"
  if ! docker compose -f infra/docker-compose.yml --env-file infra/.env exec -T api pytest -q tests/ 2>&1 | tee "$LOG_DIR/tests-$DATE.log"; then
    echo "Post-Commit-Tests rot — siehe Log."
  fi
else
  echo "Agent hat nichts committed (exit=$AGENT_EXIT) — Tests übersprungen."
fi

# ─── 5. Deploy ───────────────────────────────────────────────
echo "── Deploy ──"
make deploy

# ─── 6. Daily Report ─────────────────────────────────────────
echo "── Daily Report ──"
# Der Agent hat den Report bereits geschrieben (Schritt 7 in AGENT_INSTRUCTIONS.md).
# Falls nicht: minimaler Fallback.
if [[ ! -f "$REPORT_FILE" ]]; then
  {
    echo "# $DATE"
    echo
    echo "Der Agent hat heute keinen ausführlichen Report hinterlassen."
    echo "Letzter Commit:"
    git log -1 --pretty=format:"%h %s" || true
  } > "$REPORT_FILE"
fi

# ─── 7. Social Post ──────────────────────────────────────────
echo "── Social Update ──"
make post-update || echo "Posting fehlgeschlagen — Report bleibt für manuelles Posten."

# ─── 8. Budget nach Lauf ─────────────────────────────────────
echo "── Budget nach Lauf ──"
make budget || true

echo "$(date -Iseconds) daily agent done" >> "$LOG_DIR/heartbeat.log"
