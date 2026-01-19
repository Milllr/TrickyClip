#!/bin/bash
# fast code-only deployment (15-30 seconds)
# use this for code changes that don't modify package.json or Dockerfile
# for dependency changes, use deploy-full.sh instead

set -e

REMOTE_USER="kahuna"
REMOTE_HOST="trickyclip-server"
ZONE="us-central1-c"
REMOTE_DIR="/opt/trickyclip"

echo "⚡ fast deploy starting..."

# sync only source code (rsync is incremental - only changed files)
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

wait  # wait for both rsync to finish

# restart containers (no rebuild)
echo "🔄 restarting..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose restart backend frontend worker
"

echo "✅ done! https://trickyclip.com"

