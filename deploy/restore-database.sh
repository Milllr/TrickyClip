#!/bin/bash
# database restore script
# restores database from backup file

if [ $# -eq 0 ]; then
    echo "usage: ./restore-database.sh <backup_file.sql.gz>"
    echo ""
    echo "available backups:"
    ls -lh /opt/trickyclip/backups/
    exit 1
fi

BACKUP_FILE=$1
DEPLOY_DIR="/opt/trickyclip/deploy"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "error: backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  warning: this will replace the current database!"
echo "backup file: $BACKUP_FILE"
read -p "are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "restore cancelled"
    exit 0
fi

cd $DEPLOY_DIR

# decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "decompressing backup..."
    gunzip -c "$BACKUP_FILE" > /tmp/restore.sql
    SQL_FILE="/tmp/restore.sql"
else
    SQL_FILE="$BACKUP_FILE"
fi

# stop services that use the database
echo "stopping services..."
docker compose stop backend worker

# restore database
echo "restoring database..."
docker compose exec -T db psql -U trickyclip trickyclip < "$SQL_FILE"

# restart services
echo "restarting services..."
docker compose up -d backend worker

# cleanup temp file
if [ -f "/tmp/restore.sql" ]; then
    rm /tmp/restore.sql
fi

echo "✅ database restored successfully"
echo "verify at: https://trickyclip.com"



