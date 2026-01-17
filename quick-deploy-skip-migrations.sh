#!/bin/bash
# quick deployment that skips migrations (for emergency deploys)

cd "$(dirname "$0")"

echo "🚀 Emergency deploy (skipping migrations)..."

REMOTE_USER="kahuna"
REMOTE_HOST="trickyclip-server"
ZONE="us-central1-c"
REMOTE_DIR="/opt/trickyclip"

# upload code
echo "📦 uploading code..."
gcloud compute scp --recurse backend/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ --zone=${ZONE} --quiet
gcloud compute scp --recurse frontend/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ --zone=${ZONE} --quiet
gcloud compute scp --recurse deploy/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ --zone=${ZONE} --quiet

# rebuild containers
echo "🔨 rebuilding containers..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose up -d --build --no-deps backend frontend worker drive-sync-worker
"

echo "✅ deployed! skipped migrations."
echo "🌐 check: https://trickyclip.com/jobs"


