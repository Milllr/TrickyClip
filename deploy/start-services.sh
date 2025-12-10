#!/bin/bash
# auto-start script for trickyclip services

set -e

echo "🚀 Starting TrickyClip services..."

# ensure docker is running
if ! docker info > /dev/null 2>&1; then
    echo "⏳ Waiting for Docker to start..."
    open -a Docker
    # wait up to 60 seconds for docker to be ready
    for i in {1..60}; do
        if docker info > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

# start docker containers
cd /Users/kahuna/code/TrickyClip/deploy
echo "🐳 Starting Docker containers..."
docker compose up -d

echo "✅ TrickyClip services started!"
echo ""
echo "Services running:"
docker compose ps


