#!/bin/bash
# database backup script
# creates timestamped backup of postgresql database

DEPLOY_DIR="/opt/trickyclip/deploy"
BACKUP_DIR="/opt/trickyclip/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="trickyclip_backup_${TIMESTAMP}.sql"

# create backup directory
mkdir -p $BACKUP_DIR

echo "creating database backup: $BACKUP_FILE"

cd $DEPLOY_DIR

# create backup
docker compose exec -T db pg_dump -U trickyclip trickyclip > "${BACKUP_DIR}/${BACKUP_FILE}"

# compress backup
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

echo "backup created: ${BACKUP_DIR}/${BACKUP_FILE}.gz"

# keep only last 7 days of backups
find $BACKUP_DIR -name "trickyclip_backup_*.sql.gz" -mtime +7 -delete

# show backup size
ls -lh "${BACKUP_DIR}/${BACKUP_FILE}.gz"

# optional: upload to google cloud storage for off-site backup
# gsutil cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" gs://trickyclip-backups/


