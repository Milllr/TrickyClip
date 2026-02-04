#!/bin/bash
# trickyclip deployment script
# uses rsync for fast incremental uploads, runs migrations, and restarts services

set -e  # exit on error

REMOTE_USER="kahuna"
REMOTE_HOST="trickyclip-server"
ZONE="us-central1-c"
REMOTE_DIR="/opt/trickyclip"

echo "🚀 starting trickyclip deployment..."

# step 1: clean local cache files
echo "🧹 cleaning local cache..."
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true

# step 2: sync code using rsync (incremental - only changed files)
echo "📦 syncing backend code..."
rsync -avz --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='.git' \
    --exclude='*.log' \
    -e "gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --" \
    backend/ :${REMOTE_DIR}/backend/

echo "📦 syncing frontend code..."
rsync -avz --delete \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='.vite' \
    --exclude='*.log' \
    -e "gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --" \
    frontend/ :${REMOTE_DIR}/frontend/

echo "📦 syncing deploy configs..."
rsync -avz --delete \
    --exclude='.git' \
    -e "gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --" \
    deploy/ :${REMOTE_DIR}/deploy/

# step 3: run database migrations with alembic
echo "🗄️  running database migrations..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose exec -T backend alembic upgrade head
"

# step 4: rebuild and restart services (frontend needs rebuild since code is in image)
echo "🔄 rebuilding and restarting containers..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose build --no-cache frontend
    docker compose up -d frontend
    docker compose restart backend worker
"

# step 5: verify services are running
echo "✅ verifying services..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose ps
"

echo "✨ deployment complete!"
echo "🌐 visit https://trickyclip.com to verify"
