# TrickyClip 🎿📹

[![Deployed](https://img.shields.io/badge/deployed-trickyclip.com-blue)](https://trickyclip.com)
[![Platform](https://img.shields.io/badge/platform-Google%20Cloud-orange)]()
[![Status](https://img.shields.io/badge/status-production-green)]()

**AI-powered ski/snowboard clip organizer with Google Drive integration**

Automatically detect tricks, sort clips Tinder-style, and organize everything to Google Drive with searchable filenames.

---

## 🌐 Live Site

**https://trickyclip.com**

- **Upload:** Drop raw videos to Google Drive
- **Process:** AI finds tricks automatically
- **Sort:** Tinder-style UI for quick clip review
- **Archive:** Auto-organized to Drive with smart filenames

---

## ✨ Features

### Current (Production Ready)
- ✅ **Google Drive Workflow** - Upload to Drive → VM downloads → Process → Archive
- ✅ **ML Trick Detection** - Motion-based AI finds trick moments
- ✅ **Smart Job Queue** - RQ workers with 2-hour timeouts for video processing
- ✅ **Disk Space Management** - LRU cache, smart download queue
- ✅ **Tinder-Style Sorting** - Swipe through clips efficiently
- ✅ **Frame-by-Frame Trimming** - Precision clip editing
- ✅ **Auto-Tagging** - Person, trick, camera, FPS metadata
- ✅ **Searchable Filenames** - `2025-01-08__BackyardSession__Miller__KFED__CAM_GOPRO11__240FPS__v001.mp4`
- ✅ **Background Processing** - Multi-worker job system with live status
- ✅ **Job Monitoring** - Real-time job status sync with RQ registries
- ✅ **24/7 Uptime** - Google Cloud VM + Cloudflare Tunnel

### In Progress
- 🚧 **Cron-based sync** - Auto-download from Drive dump folder
- 🚧 **Admin dashboard** - Web UI for sync, reprocess, cleanup operations

---

## 🏗️ Architecture

### Tech Stack
```
Frontend:  React + TypeScript + Vite + Tailwind
Backend:   FastAPI + Python 3.11 + SQLModel
Database:  PostgreSQL (with Alembic migrations)
Queue:     Redis + RQ (2-worker setup with 2h timeouts)
Storage:   VM disk (temp) + Google Drive (permanent)
Detection: OpenCV + motion analysis (ML-based)
Hosting:   Google Cloud e2-medium VM + Docker Compose
Tunnel:    Cloudflare (encrypted, no open ports)
```

### Data Flow

#### 1. Upload & Download Flow (Google Drive → VM)
```
User uploads raw video to Drive "dump" folder
    ↓
Trigger sync: POST /api/admin/sync-from-drive
    ↓
VM checks disk space (requires file size + 5GB buffer)
    ↓
Downloads video to /data/originals/
    ↓
Registers in DB with drive_file_id
    ↓
Queues analysis job (timeout: 2h)
```

#### 2. Analysis Flow (ML Detection)
```
Worker picks up analyze_original_file job
    ↓
Generate analysis proxy (720p for efficiency)
    ↓
Stage 1: Motion + Audio detection
  - ORB keypoint tracking for camera-stabilized motion
  - Audio energy analysis for impact sounds
  - Candidate window fusion
    ↓
Stage 2 (optional): ML scoring with MoViNet
  - Filters candidates by confidence threshold
    ↓
Creates CandidateSegment records (UNREVIEWED status)
    ↓
Moves raw video to "processed/{date}/" on Drive (server-side)
    ↓
Keeps local copy for sorting (LRU eviction later)
    ↓
Ready for /sort!
```

#### 3. Sort & Render Flow
```
User opens /sort → gets next UNREVIEWED segment
    ↓
Adjusts trim points, tags person/trick
    ↓
Saves → creates FinalClip record
    ↓
Queues render_and_upload_clip job
    ↓
Worker: FFmpeg renders (ffmpeg -c copy)
    ↓
Uploads small clip to Drive (bypasses quota!)
    ↓
Organized: Drive/2025/{date}/{person}/{trick}/
    ↓
Deletes local files to free space
```

---

## 🚀 Deployment Commands

### Deploy Changes to VM
```bash
# From project root
cd /Users/kahuna/code/TrickyClip
./deploy/deploy.sh
```

This script:
1. Cleans local cache
2. Uploads backend + frontend to VM
3. Runs database migrations
4. Rebuilds Docker containers
5. Restarts services

### SSH into VM
```bash
# Basic SSH
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c

# SSH with command
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c --command="cd /opt/trickyclip/deploy && docker compose ps"

# SSH to specific project
gcloud compute ssh kahuna@trickyclip-server \
  --project=graphic-parsec-480000-i8 \
  --zone=us-central1-c
```

### Check Services
```bash
# On VM - check all services
cd /opt/trickyclip/deploy
docker compose ps

# Check tunnel
sudo systemctl status cloudflared-tunnel

# Check disk space
df -h
```

### View Logs
```bash
# Worker logs (live)
docker compose logs worker -f

# Backend logs
docker compose logs backend -f

# All logs
docker compose logs -f

# Last 50 lines
docker compose logs worker --tail=50

# Tunnel logs
sudo journalctl -u cloudflared-tunnel -f
```

### Restart Services
```bash
# Restart specific service
docker compose restart worker
docker compose restart backend

# Restart all
docker compose restart

# Full rebuild
docker compose up -d --build
```

---

## 🎯 Common Operations

#Recurse upload
```bash
gcloud compute scp --recurse backend/ trickyclip-server:/opt/trickyclip/backend --zone=us-central1-c  
```

### Trigger Drive Sync
```bash
# From anywhere
curl -X POST https://trickyclip.com/api/admin/sync-from-drive

# From VM
curl -X POST http://localhost:8001/api/admin/sync-from-drive
```

### Reprocess Failed Videos
```bash
# Get file ID from database, then:
curl -X POST https://trickyclip.com/api/admin/reprocess/{file_id}
```

### Check Job Status
```bash
# API
curl https://trickyclip.com/api/jobs/

# Or visit: https://trickyclip.com/jobs
```

### Database Operations
```bash
# Connect to DB
docker compose exec db psql -U trickyclip trickyclip

# Check segments
docker compose exec db psql -U trickyclip trickyclip -c "SELECT status, COUNT(*) FROM candidate_segments GROUP BY status;"

# Check files
docker compose exec db psql -U trickyclip trickyclip -c "SELECT original_filename, processing_status FROM original_files ORDER BY created_at DESC LIMIT 10;"

# Run migration
docker compose exec db psql -U trickyclip trickyclip -c "ALTER TABLE original_files ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR;"
```

### Cleanup Operations
```bash
# Storage cleanup
curl -X POST https://trickyclip.com/api/admin/storage/cleanup

# Aggressive cleanup (older files)
curl -X POST https://trickyclip.com/api/admin/storage/cleanup \
  -H "Content-Type: application/json" \
  -d '{"aggressive": true}'

# Check storage
curl https://trickyclip.com/api/admin/storage
```

---

## 🗂️ Google Drive Setup

### Folder Structure
```
TrickyClip Archive/
├── dump/                    ← Manual uploads (raw videos)
├── processed/               ← Analyzed raw videos (auto-moved by VM)
│   ├── 2025-01-08/
│   │   └── 2025-01-08_DSC_2495.MP4
│   └── 2025-01-09/
└── 2025/                    ← Final clips (auto-uploaded)
    ├── 2025-01-08 - Backyard Session/
    │   ├── Miller_Downey/
    │   │   ├── KFED/
    │   │   │   └── 2025-01-08__BackyardSession__Miller_Downey__KFED__CAM_GOPRO11__240FPS__v001.mp4
    │   │   └── Britney/
    │   └── Mitchell/
    └── 2025-01-15 - Night Rails/
```

### Required Environment Variables
```bash
# In /opt/trickyclip/backend/.env
GOOGLE_DRIVE_ROOT_FOLDER_ID=1qkk0IkkZy8CaR1iicx2eLHn9r8uk-geM
GOOGLE_DRIVE_DUMP_FOLDER_ID=1UsqnRommTK4fDM6zNZEjv1KfzdP74FUk  
GOOGLE_DRIVE_PROCESSED_FOLDER_ID=<your_processed_folder_id>
```

### Service Account
- Email: `trickyclip@graphic-parsec-480000-i8.iam.gserviceaccount.com`
- Must have **Editor** access to:
  - Root folder (TrickyClip Archive)
  - Dump folder
  - Processed folder
- Credentials: `/app/secrets/graphic-parsec-480000-i8-0552e472ced1.json`

---

## 📊 Database Schema

### Key Models

**OriginalFile** - Raw uploaded videos
- `drive_file_id` - Drive file ID for downloaded videos
- `file_size_bytes` - For disk space management
- `processing_status` - pending, analyzing, completed, failed, archived

**CandidateSegment** - Detected trick moments
- `status` - UNREVIEWED, ACCEPTED, TRASHED
- `confidence_score` - ML detection confidence
- `detection_method` - motion, manual, etc.

**FinalClip** - Saved clips
- `drive_file_id` - Uploaded clip in Drive
- `is_uploaded_to_drive` - Upload status
- `filename` - Searchable schema

**Job** - Background job tracking
- `rq_job_id` - Links to Redis queue
- `status` - queued, running, completed, failed
- `progress_percent` - Live progress tracking

---

## 🎬 Video Processing

### FFmpeg Commands
```bash
# Extraction (used for clips)
ffmpeg -ss START_SEC -i input.mp4 -t DURATION_SEC -c copy output.mp4

# Metadata extraction
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

### ML Detection
- **Stage 1:** Motion + Audio analysis (always runs)
  - Stabilized motion detection using ORB keypoints + homography
  - Audio energy analysis for impact detection
  - Candidate window fusion with configurable thresholds
- **Stage 2:** ML scoring with MoViNet (optional, requires trained model)
  - TFLite runtime for efficient inference
  - Filters Stage 1 candidates to 5-10 high-confidence segments
- **Output:** Segments with confidence scores (typically 5-15 per video)
- **Tuning:** Adjustable thresholds in environment variables (see [DETECTION-PIPELINE.md](DETECTION-PIPELINE.md))

### Job System
- **Queue:** RQ (Redis Queue)
- **Workers:** 2 parallel workers
- **Timeout:** 2 hours for analysis jobs
- **Retry:** Automatic on failure
- **Monitoring:** Live status sync with RQ registries

---

## 📝 File Naming Schema

```
YYYY-MM-DD__Session__Person__Trick__CAMID__FPS__v###.mp4
```

**Example:**
```
2025-01-08__BackyardSession__Miller_Downey__KFED__CAM_GOPRO11__240FPS__v001.mp4
```

**Benefits:**
- ✅ Chronological sorting
- ✅ Full-text search works
- ✅ All metadata in filename
- ✅ Version control (v001, v002...)

---

## 🔄 Workflows

### Daily Workflow
1. **Upload videos** to Drive "dump" folder manually
2. **Trigger sync** (or wait for cron): `POST /api/admin/sync-from-drive`
3. **Monitor jobs** at https://trickyclip.com/jobs
4. **Sort clips** at https://trickyclip.com/sort when ready
5. **Browse results** at https://trickyclip.com/clips

### Troubleshooting Workflow
1. **Check jobs page** - Are jobs stuck?
2. **Check worker logs** - `docker compose logs worker -f`
3. **Check disk space** - `df -h` (need 5GB free minimum)
4. **Reprocess if needed** - `POST /api/admin/reprocess/{file_id}`
5. **Check Drive permissions** - Service account has Editor access?

---

## 🎯 Next Steps & Goals

### Immediate Priorities
- [ ] **Cron job setup** - Auto-sync from dump folder every hour
- [ ] **Admin web UI** - Button to trigger sync, view storage, reprocess files
- [ ] **Better error handling** - Retry failed jobs with exponential backoff
- [ ] **Webhook notifications** - Discord/Slack when videos are ready to sort

### Short Term (Next Month)
- [ ] **Batch processing** - Download multiple videos in parallel
- [ ] **Progress indicators** - Real-time download/analysis progress
- [ ] **Video thumbnails** - Preview before sorting
- [ ] **Keyboard shortcuts** - Faster sorting workflow
- [ ] **Mobile optimization** - Sort on phone

### Medium Term (Next 3 Months)
- [ ] **Multi-camera sync** - Stitch clips from multiple angles
- [ ] **Advanced ML** - Trick type detection (identify specific tricks)
- [ ] **Collaboration** - Multiple people sorting simultaneously
- [ ] **Analytics dashboard** - Session stats, trick counts
- [ ] **Clip collections** - Group related clips into edits

### Long Term (Future)
- [ ] **Auto-editing** - Generate highlight reels automatically
- [ ] **Social sharing** - Direct upload to Instagram/TikTok
- [ ] **Mobile app** - Native iOS/Android
- [ ] **Live processing** - GoPro live stream → instant clip detection
- [ ] **Team features** - Multiple crews, private archives

---

## 💡 Performance & Limits

### Current Capacity
- **VM:** e2-medium (2 vCPU, 4GB RAM, 50GB disk)
- **Workers:** 2 parallel
- **Concurrent uploads:** 1-2 at a time
- **Video size:** Up to 10GB per file
- **Processing time:** ~2-5 minutes per GB
- **Storage:** LRU eviction keeps disk under 40GB

### Scaling Options
1. **More workers** - Increase replicas in docker-compose.yml
2. **Bigger VM** - Upgrade to e2-standard-4 (4 vCPU, 16GB)
3. **Cloud storage** - Move to Google Cloud Storage
4. **Caching** - Redis cache for API responses
5. **CDN** - CloudFlare for video streaming

---

## 🔒 Security

- **Cloudflare Tunnel** - Encrypted, no open ports on VM
- **SSL/TLS** - Automatic HTTPS
- **Service account** - Limited Drive permissions
- **Secrets** - All credentials gitignored
- **Database** - Internal Docker network only
- **API** - Can add auth middleware later

---

## 📚 Documentation

- **[DETECTION-PIPELINE.md](DETECTION-PIPELINE.md)** - ML detection system details
- **[deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md)** - Deployment guide
- **[deploy/DEPLOY-CHECKLIST.md](deploy/DEPLOY-CHECKLIST.md)** - Quick reference
- **[backend/README.md](backend/README.md)** - Backend architecture
- **[secrets/README.md](secrets/README.md)** - Credentials info

---

## 💰 Cost

### Development
- **Local:** FREE

### Production (Google Cloud)
- **VM (e2-medium):** ~$25/month
- **Storage (50GB):** ~$2/month
- **Network egress:** ~$1-5/month
- **Total:** ~$28-32/month

**First 10 months:** FREE with $300 Google Cloud credits 🎉

---

## 🎉 Status

**✅ Production Ready**

Live at https://trickyclip.com with:
- Google Drive integration working
- ML trick detection operational
- Job queue with monitoring
- Auto-restart on failures
- 24/7 uptime

---

## 🤝 Contributing

Built by [@Miller-Downey](https://github.com/Miller-Downey)

To contribute:
1. Fork the repo
2. Create feature branch
3. Test locally with `docker-compose up`
4. Submit PR

---

## 🆘 Quick Help

### Something broken?
```bash
# Check everything
cd /opt/trickyclip/deploy && docker compose ps

# Restart everything
docker compose restart

# Check logs
docker compose logs -f
```

### Videos not downloading?
1. Check Drive permissions (service account has Editor access?)
2. Check folder IDs in `.env`
3. Check disk space: `df -h`
4. Check logs: `docker compose logs worker -f`

### Jobs stuck?
1. Visit https://trickyclip.com/jobs
2. Check worker logs: `docker compose logs worker -f`
3. Restart workers: `docker compose restart worker`
4. Reprocess: `curl -X POST https://trickyclip.com/api/admin/reprocess/{file_id}`

### Need more help?
Check worker logs for detailed error messages:
```bash
docker compose logs worker --tail=100
```

---

**Ready to organize your clips? Upload to Drive and let TrickyClip handle the rest! 🎿📹**
