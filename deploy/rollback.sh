#!/bin/bash
# trickyclip rollback script
# reverts to previous database migration and docker images

set -e

REMOTE_USER="kahuna"
REMOTE_HOST="trickyclip-server"
ZONE="us-central1-c"
REMOTE_DIR="/opt/trickyclip"

echo "⚠️  starting trickyclip rollback..."

# step 1: rollback database migration
echo "🗄️  rolling back database migration..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}
    docker compose exec -T backend alembic downgrade -1
"

# step 2: restart services with previous images
echo "🔄 restarting services..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose restart backend frontend worker
"

# step 3: verify services
echo "✅ verifying services..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose ps
    docker compose logs backend --tail=20
"

echo "✨ rollback complete!"
echo "🌐 visit https://trickyclip.com to verify"
echo ""
echo "ℹ️  note: code files on VM are not rolled back, only database and containers"
echo "ℹ️  to fully rollback code, restore from git or backup"




