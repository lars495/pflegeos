#!/usr/bin/env bash
# Tägliches verschlüsseltes Backup nach Hetzner Storage Box.
#
# Voraussetzungen:
#   - rclone konfiguriert als Remote "storagebox"
#   - age installiert mit Public Key in ~/.config/age/backup.pub

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose -f infra/docker-compose.yml --env-file infra/.env"
STAMP=$(date +%Y%m%d-%H%M)
BACKUP_DIR="/tmp/pflegeos-backup-$STAMP"
mkdir -p "$BACKUP_DIR"

echo "── DB-Dump ──"
$COMPOSE exec -T db pg_dump -U "$POSTGRES_USER" -d pflegeos > "$BACKUP_DIR/db.sql"

echo "── Verschlüsseln ──"
PUBKEY="${AGE_RECIPIENT:-$HOME/.config/age/backup.pub}"
if [[ ! -f "$PUBKEY" ]]; then
  echo "Kein age public key unter $PUBKEY — Backup unverschlüsselt skipped."
  exit 1
fi
age -R "$PUBKEY" -o "$BACKUP_DIR/db.sql.age" "$BACKUP_DIR/db.sql"
rm "$BACKUP_DIR/db.sql"

echo "── Upload ──"
rclone copy "$BACKUP_DIR" storagebox:pflegeos/backups/$STAMP/ --progress

rm -rf "$BACKUP_DIR"
echo "Backup $STAMP ok"
