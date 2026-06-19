#!/usr/bin/env bash
# ── Aurum PMS — PostgreSQL backup ──────────────────────────────────────────
#
# Usage:
#   bash scripts/backup-db.sh                    # backs up to ./backups/
#   bash scripts/backup-db.sh /mnt/backups       # custom output dir
#
# To automate — add to crontab (crontab -e):
#   0 2 * * * cd /path/to/aurum-pms && bash scripts/backup-db.sh >> /var/log/aurum-backup.log 2>&1
#
# Keeps the last 7 daily backups. Older ones are deleted automatically.

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="pms_${TIMESTAMP}.sql.gz"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting backup → $BACKUP_DIR/$FILENAME"

# Dump via the running postgres container (works with both compose files)
if docker compose -f docker-compose.prod.yml ps db 2>/dev/null | grep -q "Up\|running"; then
  COMPOSE_FILE="docker-compose.prod.yml"
elif docker compose ps db 2>/dev/null | grep -q "Up\|running"; then
  COMPOSE_FILE="docker-compose.yml"
else
  echo "ERROR: postgres container is not running."
  exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U pms_admin -d pms --no-password \
  | gzip > "$BACKUP_DIR/$FILENAME"

SIZE=$(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1)
echo "[$(date -Iseconds)] ✓ Backup complete — $FILENAME ($SIZE)"

# Prune backups older than KEEP_DAYS
DELETED=$(find "$BACKUP_DIR" -name "pms_*.sql.gz" -mtime +$KEEP_DAYS -print -delete | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
  echo "[$(date -Iseconds)] Pruned $DELETED backup(s) older than ${KEEP_DAYS} days"
fi

echo "[$(date -Iseconds)] Backups in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/pms_*.sql.gz 2>/dev/null || echo "  (none)"
