#!/usr/bin/env bash
# Installiert Cron-Jobs für täglichen Build + monatlichen Legal-Audit.
# Idempotent: vorhandene PflegeOS-Einträge werden ersetzt.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v "# PflegeOS:" > "$TMP" || true

cat >> "$TMP" <<EOF
# PflegeOS: täglicher Build-Agent (03:00 Berlin)
0 3 * * * cd $ROOT && ./scripts/daily_agent.sh >> $ROOT/logs/daily.log 2>&1
# PflegeOS: monatlicher Legal-Audit (1. Tag des Monats, 02:00 Berlin)
0 2 1 * * cd $ROOT && /usr/bin/make legal-audit >> $ROOT/logs/legal.log 2>&1
# PflegeOS: tägliches Backup (04:00 Berlin)
0 4 * * * cd $ROOT && /usr/bin/make backup >> $ROOT/logs/backup.log 2>&1
EOF

crontab "$TMP"
rm "$TMP"
echo "Cron installiert. Aktuelle Jobs:"
crontab -l | grep PflegeOS
