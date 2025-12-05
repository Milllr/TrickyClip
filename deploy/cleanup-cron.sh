#!/bin/bash
# automated storage cleanup script
# run via cron every 6 hours to keep storage under control

DEPLOY_DIR="/opt/trickyclip/deploy"
LOG_FILE="/var/log/trickyclip/cleanup_$(date +%Y%m%d).log"

echo "$(date): starting automated cleanup" >> $LOG_FILE

cd $DEPLOY_DIR

# trigger cleanup via API
docker compose exec -T backend python -c "
from app.services.storage_manager import storage_manager
result = storage_manager.run_cleanup(aggressive=False)
print(f'Cleanup complete: {result}')
" >> $LOG_FILE 2>&1

echo "$(date): cleanup finished" >> $LOG_FILE

