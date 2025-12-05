# TrickyClip Architecture

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         USERS                                │
│              (Upload, Sort, Browse Clips)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              CLOUDFLARE CDN (Worldwide)                      │
│         - SSL/TLS Encryption                                 │
│         - DDoS Protection                                    │
│         - Edge Caching                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Encrypted Tunnel
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           GOOGLE CLOUD VM (24/7 Server)                      │
│                                                              │
│  ┌─────────────────────────────────────────────────┐        │
│  │          Cloudflare Tunnel                      │        │
│  │     (Routes traffic to local services)          │        │
│  └──────────┬──────────────────────────────────────┘        │
│             │                                                │
│             ├──► /api/* ──────────────┐                      │
│             │                         │                      │
│             └──► /* ──────────────┐   │                      │
│                                   │   │                      │
│  ┌────────────────────────────────┼───┼──────────────────┐  │
│  │         DOCKER CONTAINERS      │   │                  │  │
│  │                                │   │                  │  │
│  │  ┌─────────────────────────────▼───┴─────┐            │  │
│  │  │     FastAPI Backend :8001             │            │  │
│  │  │  - REST API                           │            │  │
│  │  │  - File Upload Handling               │            │  │
│  │  │  - Metadata Management                │            │  │
│  │  │  - Job Queue Integration              │            │  │
│  │  └───────────┬────────────────────────────┘            │  │
│  │              │                                         │  │
│  │  ┌───────────▼─────────────────────────┐              │  │
│  │  │   React Frontend :3000             │              │  │
│  │  │  - /upload - Drag & drop videos    │              │  │
│  │  │  - /sort - Tinder-style UI         │              │  │
│  │  │  - /clips - Browse all clips       │              │  │
│  │  └────────────────────────────────────┘              │  │
│  │                                                       │  │
│  │  ┌──────────────────────────────────┐                │  │
│  │  │   RQ Worker (Background)        │                │  │
│  │  │  - Video Processing             │                │  │
│  │  │  - AI Trick Detection           │                │  │
│  │  │  - FFmpeg Trimming              │                │  │
│  │  │  - Google Drive Upload          │                │  │
│  │  └───────────┬─────────────────────┘                │  │
│  │              │                                       │  │
│  │  ┌───────────▼─────────────┐                        │  │
│  │  │    Redis Queue          │                        │  │
│  │  │  - Job Management       │                        │  │
│  │  └─────────────────────────┘                        │  │
│  │                                                      │  │
│  │  ┌──────────────────────────┐                       │  │
│  │  │   PostgreSQL Database    │                       │  │
│  │  │  - People                │                       │  │
│  │  │  - Tricks                │                       │  │
│  │  │  - Original Files        │                       │  │
│  │  │  - Candidate Segments    │                       │  │
│  │  │  - Final Clips           │                       │  │
│  │  └──────────────────────────┘                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         LOCAL STORAGE (/data)                        │  │
│  │  - /data/originals/     - Uploaded raw videos       │  │
│  │  - /data/candidates/    - Detected segments         │  │
│  │  - /data/final_clips/   - Rendered final clips      │  │
│  └──────────────────────────────────────────────────────┘  │
│                     │                                       │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      │ Google Drive API
                      ▼
          ┌──────────────────────────┐
          │    GOOGLE DRIVE          │
          │                          │
          │  TrickyClip Archive/     │
          │    2024/                 │
          │      Session/            │
          │        Person/           │
          │          Trick/          │
          │            clips.mp4     │
          └──────────────────────────┘
```

## 🔄 Data Flow

### 1. Upload Flow
```
User uploads video
    ↓
Frontend sends to /api/upload
    ↓
Backend saves to /data/originals/
    ↓
Creates OriginalFile record in DB
    ↓
Enqueues processing job in Redis
    ↓
Worker picks up job
    ↓
Runs AI detection (finds trick moments)
    ↓
Creates CandidateSegment records
    ↓
Ready for sorting!
```

### 2. Sort Flow
```
User opens /sort
    ↓
Frontend calls /api/sort/next
    ↓
Backend returns next unreviewed segment
    ↓
User adjusts trim points
    ↓
User tags person + trick
    ↓
Frontend calls /api/sort/save
    ↓
Backend creates FinalClip record
    ↓
Enqueues render job in Redis
    ↓
Worker renders video with FFmpeg
    ↓
Worker uploads to Google Drive
    ↓
Stores drive_file_id in DB
    ↓
Done! ✓
```

### 3. Browse Flow
```
User opens /clips
    ↓
Frontend calls /api/clips
    ↓
Backend queries FinalClip records
    ↓
Returns list with filters
    ↓
User clicks a clip
    ↓
Opens /clip/:id
    ↓
Can re-edit or download
```

## 🗄️ Database Schema

### People
```sql
- id (UUID)
- display_name (e.g., "Miller Downey")
- slug (e.g., "Miller_Downey")
- created_at
```

### Tricks
```sql
- id (UUID)
- name (e.g., "KFED", "Britney")
- category (RAIL, JUMP, BROLL)
- direction (FS, BS, etc.)
```

### OriginalFile
```sql
- id (UUID)
- stored_path (/data/originals/xxx.mp4)
- file_hash (SHA256)
- camera_id (CAM_GOPRO11)
- fps_label (240FPS)
- duration_ms
- recorded_at (date)
- session_name
```

### CandidateSegment
```sql
- id (UUID)
- original_file_id (FK)
- start_ms
- end_ms
- status (UNREVIEWED, IN_PROGRESS, ACCEPTED, TRASHED)
- locked_by, locked_at
```

### FinalClip
```sql
- id (UUID)
- candidate_segment_id (FK)
- original_file_id (FK)
- person_id (FK, nullable)
- trick_id (FK, nullable)
- category (TRICK, BROLL, CRASH)
- start_ms, end_ms (final trimmed)
- camera_id, fps_label, date
- stored_path (local)
- drive_file_id (Google Drive)
- filename (searchable)
- created_at, updated_at
```

## 🎯 Key Features

### Background Processing
- **Redis Queue (RQ)** manages all background jobs
- **Worker container** runs continuously
- Jobs are retried automatically on failure
- Multiple workers can run in parallel

### Filename Schema
```
YYYY-MM-DD__Session__Person__Trick__CAMID__FPS__v###.mp4

Example:
2024-12-01__BackyardRails__Miller_Downey__KFED__CAM_GOPRO11__240FPS__v001.mp4
```

**Searchable by:**
- Date: `2024-12-01`
- Session: `BackyardRails`
- Person: `Miller`
- Trick: `KFED`
- Camera: `CAM_GOPRO11`
- FPS: `240FPS`

### Google Drive Structure
```
TrickyClip Archive/
  2024/
    2024-12-01 - Backyard Rails/
      Miller_Downey/
        KFED/
          2024-12-01__BackyardRails__Miller_Downey__KFED__CAM_GOPRO11__240FPS__v001.mp4
          v002.mp4
        Britney/
          clips...
      Mitchell/
        Back270_Out/
          clips...
    2024-12-15 - Night Session/
      ...
  2025/
    ...
```

## 🔒 Security

- **Cloudflare Tunnel:** Encrypted, no open ports
- **SSL/TLS:** Automatic HTTPS via Cloudflare
- **No public database:** PostgreSQL only accessible within Docker network
- **Service account:** Google Drive access via service account (not user creds)
- **Secrets management:** All credentials in `.env` and `secrets/` (gitignored)

## 📊 Resource Usage

### Google Cloud VM (e2-medium)
- **CPU:** 2 vCPUs (can spike to 100% during video processing)
- **RAM:** 4 GB (adequate for 2-3 parallel video jobs)
- **Disk:** 50 GB (stores originals temporarily)
- **Network:** Fast enough for video uploads

### Cost Estimates
- **VM:** ~$25/month
- **Storage:** ~$2/month (50GB)
- **Egress:** ~$1-5/month
- **Total:** ~$28-32/month (**FREE with $300 credits for 10 months**)

## 🚀 Scalability

### Current Setup (MVP)
- ✅ Handles 1-2 concurrent uploads
- ✅ Processes videos in background
- ✅ Supports unlimited users for sorting
- ✅ Good for small crew (~10-20 people)

### Future Scaling Options
1. **More workers:** Add more worker containers for parallel processing
2. **Bigger VM:** Upgrade to e2-standard-4 (4 vCPU, 16 GB) for $100/month
3. **Cloud Storage:** Move from VM disk to Google Cloud Storage
4. **CDN for videos:** Serve videos directly from Google Drive or GCS
5. **Database:** Use Cloud SQL instead of Docker PostgreSQL
6. **Load balancer:** Multiple backend containers

## 🎬 Video Processing Pipeline

```
Original Video (e.g., 30 minutes @ 240fps)
    ↓
AI Detection: Find trick moments
    ↓
Create 3-4 second segments
    ↓
User sorts/trims each segment
    ↓
FFmpeg renders final clip (-c copy for speed)
    ↓
Upload to Google Drive
    ↓
Local copy kept for re-editing
```

### FFmpeg Command
```bash
ffmpeg -ss START_SEC -i /data/originals/xxx.mp4 \
       -t DURATION_SEC -c copy \
       /data/final_clips/output.mp4
```

Uses `-c copy` for speed (no re-encoding, just copying streams).

## 🔄 Auto-Restart Strategy

### Docker Containers
- `restart: always` in docker-compose.yml
- Systemd service: `trickyclip-docker.service`
- Starts on boot, restarts on failure

### Cloudflare Tunnel
- Systemd service: `cloudflared-tunnel.service`
- Restarts every 5 seconds if it crashes
- Enabled on boot

### Result
Everything survives:
- VM reboot
- Container crash
- Tunnel disconnect
- Worker errors

## 📈 Monitoring

### Check Everything is Running
```bash
# docker containers
docker-compose ps

# tunnel
sudo systemctl status cloudflared-tunnel

# worker jobs
docker-compose logs -f worker

# disk space
df -h
```

### Key Metrics to Watch
- **Disk usage:** Don't fill up the 50GB
- **Worker queue:** Check Redis queue depth
- **Upload rate:** How many videos per day
- **Processing time:** How long per video

## 🎉 Summary

TrickyClip is a **full-stack web application** that:
- Runs 24/7 on Google Cloud (free for ~10 months)
- Accepts video uploads from anywhere
- Automatically detects trick moments
- Provides an efficient sorting interface
- Renders final clips with proper naming
- Uploads organized clips to Google Drive
- Survives reboots and crashes
- Scales from 1 user to 100+ users

**Your laptop:** Can stay off! The server handles everything. 🚀

