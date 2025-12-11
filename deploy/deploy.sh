#!/bin/bash
# trickyclip deployment script
# uploads code changes, runs migrations, and restarts services with zero downtime

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
find frontend -name "node_modules" -prune -o -type f -name ".DS_Store" -delete 2>/dev/null || true

# step 1b: upload code changes
echo "📦 uploading backend code..."
gcloud compute scp --recurse backend/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ --zone=${ZONE}

echo "📦 uploading frontend code..."
gcloud compute scp --recurse frontend/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ --zone=${ZONE}

echo "📦 uploading deploy configs..."
gcloud compute scp --recurse deploy/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ --zone=${ZONE}

# step 2: run database migrations with alembic
echo "🗄️  running database migrations..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose exec -T backend alembic upgrade head
"

# step 3: rebuild and restart services
echo "🔨 rebuilding containers..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose up -d --build --no-deps backend frontend worker
"

# step 4: verify services are running
echo "✅ verifying services..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose ps
    docker compose logs backend --tail=20
"

echo "✨ deployment complete!"
echo "🌐 visit https://trickyclip.com to verify"

