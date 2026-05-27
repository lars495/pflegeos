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
AGENT_PROMPT=$(cat AGENT_INSTRUCTIONS.md)

# Wir bevorzugen claude (Claude Code CLI). Hermes als Fallback.
if command -v claude >/dev/null 2>&1; then
  echo "$AGENT_PROMPT" | claude --print --model claude-sonnet-4-6 \
    --permission-mode acceptEdits \
    --append-system-prompt "Heutiges Datum: $DATE. Repo: $ROOT." \
    > "$LOG_DIR/agent-$DATE.log" 2>&1 || true
elif command -v hermes >/dev/null 2>&1; then
  hermes run --prompt-file AGENT_INSTRUCTIONS.md \
    --cwd "$ROOT" > "$LOG_DIR/agent-$DATE.log" 2>&1 || true
else
  echo "Kein Agent-CLI gefunden (claude oder hermes). Abbruch."
  exit 1
fi

# ─── 4. Tests ────────────────────────────────────────────────
echo "── Tests ──"
if ! make test; then
  echo "Tests rot — kein Deploy." >> "$REPORT_FILE.tmp"
  make daily-report-failure DATE="$DATE" || true
  exit 1
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
