#!/bin/bash
# full deployment with Docker rebuild (1-2 minutes)
# use this when package.json, Dockerfile, or dependencies change

set -e

REMOTE_USER="kahuna"
REMOTE_HOST="trickyclip-server"
ZONE="us-central1-c"
REMOTE_DIR="/opt/trickyclip"

echo "🔨 full rebuild deploy starting..."

# sync all code
echo "📦 syncing code..."
rsync -avz --delete \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
    --exclude='.git' --exclude='*.log' \
    -e "gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --" \
    backend/ :${REMOTE_DIR}/backend/ &

rsync -avz --delete \
    --exclude='node_modules' --exclude='.git' --exclude='dist' \
    --exclude='.vite' --exclude='*.log' \
    -e "gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --" \
    frontend/ :${REMOTE_DIR}/frontend/ &

rsync -avz --delete \
    --exclude='.git' \
    -e "gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --" \
    deploy/ :${REMOTE_DIR}/deploy/ &

wait  # wait for all rsync to finish

# run migrations
echo "🗄️  running migrations..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose exec -T backend alembic upgrade head 2>/dev/null || true
"

# full rebuild with fresh npm install
echo "🔨 rebuilding containers..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose up -d --build --force-recreate backend frontend worker
"

# verify
echo "✅ verifying..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose ps
"

echo "✨ full rebuild complete! https://trickyclip.com"

