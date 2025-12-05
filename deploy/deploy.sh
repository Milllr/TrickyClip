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

# step 2: run database migrations (manual SQL for now)
echo "🗄️  running database migrations..."
gcloud compute ssh ${REMOTE_USER}@${REMOTE_HOST} --zone=${ZONE} --command="
    cd ${REMOTE_DIR}/deploy
    docker compose exec -T db psql -U trickyclip trickyclip << 'EOF'
-- add new columns to original_files
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS width INTEGER DEFAULT 0;
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS height INTEGER DEFAULT 0;
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR DEFAULT 'unknown';
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS resolution_label VARCHAR DEFAULT 'unknown';
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS processing_status VARCHAR DEFAULT 'pending';
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS analysis_progress_percent INTEGER DEFAULT 0;

-- add new columns to candidate_segments
ALTER TABLE candidate_segments ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.5;
ALTER TABLE candidate_segments ADD COLUMN IF NOT EXISTS detection_method VARCHAR DEFAULT 'basic';

-- add new columns to final_clips
ALTER TABLE final_clips ADD COLUMN IF NOT EXISTS resolution_label VARCHAR DEFAULT 'unknown';
ALTER TABLE final_clips ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR DEFAULT 'unknown';
ALTER TABLE final_clips ADD COLUMN IF NOT EXISTS drive_url VARCHAR;
ALTER TABLE final_clips ADD COLUMN IF NOT EXISTS is_uploaded_to_drive BOOLEAN DEFAULT false;
ALTER TABLE final_clips ADD COLUMN IF NOT EXISTS clip_hash VARCHAR;

-- create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    rq_job_id VARCHAR UNIQUE NOT NULL,
    job_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    file_id UUID,
    clip_id UUID,
    progress_percent INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_jobs_rq_job_id ON jobs(rq_job_id);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS ix_jobs_file_id ON jobs(file_id);
CREATE INDEX IF NOT EXISTS ix_jobs_clip_id ON jobs(clip_id);
CREATE INDEX IF NOT EXISTS ix_jobs_created_at ON jobs(created_at);
EOF
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

