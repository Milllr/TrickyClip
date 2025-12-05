# TrickyClip 🎿📹

[![Deployed](https://img.shields.io/badge/deployed-trickyclip.com-blue)](https://trickyclip.com)
[![Platform](https://img.shields.io/badge/platform-Google%20Cloud-orange)]()
[![Status](https://img.shields.io/badge/status-production-green)]()

A web app for automatically organizing ski/snowboard clips with AI-powered trick detection.

## 🌐 Live Site

**https://trickyclip.com**

## High-level product spec

TrickyClip is a web app for ski/snowboard clip sorting.

Anyone with the password can upload long raw videos → `/upload`

A background pipeline analyzes them and creates short candidate segments from trick-ish moments

`/sort` shows an endless Tinder-style queue of short clips:

*   scrub / trim in–out points
*   tag person + trick (+ category)
*   auto-filled camera + FPS + date
*   hit “Save” to export a final clip

Final clips are rendered from the original file, named using a searchable schema, and stored inside a structured Google Drive archive.

Each final clip has a permanent URL (`/clip/:id`) and can be reopened later, re-trimmed, and re-exported.

## Tech stack

### Frontend
*   React + Vite + TypeScript
*   UI lib: Tailwind + headless UI (or Radix)
*   Video player: use native `<video>` + custom scrubber

### Backend
*   Python 3.11+
*   FastAPI (REST API, async)
*   SQLModel (SQLAlchemy wrapper)
*   Postgres for DB
*   Redis for job queue
*   RQ for background tasks

### Video processing
*   FFmpeg + ffprobe

### Infra
*   Docker Compose

## Milestones

### Milestone 1 – Minimal end-to-end skeleton ✅
*   Backend FastAPI + DB (Postgres)
*   Models created
*   `/api/upload` endpoint (saves file, extracts metadata, creates dummy segments)
*   `/api/sort/next`, `/api/sort/save`, `/api/sort/trash` implemented
*   `render_and_upload_clip` job with Google Drive integration
*   Frontend `/sort` page (video player, trim sliders, save/trash)
*   **Status:** COMPLETE

## 🚀 Quick Start

### Local Development

```bash
# start all services
cd deploy
docker-compose up -d

# check status
docker-compose ps

# view logs
docker-compose logs -f
```

Visit:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001

### Deploy to Production

See **[GOOGLE-CLOUD-DEPLOY.md](deploy/GOOGLE-CLOUD-DEPLOY.md)** for complete deployment guide.

Quick version:
1. Create Google Cloud VM (e2-medium)
2. Run setup script
3. Transfer files
4. Start services
5. Site is live at https://trickyclip.com

**Cost:** FREE for ~10 months with Google Cloud $300 credits

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and data flow
- **[deploy/GOOGLE-CLOUD-DEPLOY.md](deploy/GOOGLE-CLOUD-DEPLOY.md)** - Full deployment guide
- **[deploy/DEPLOY-CHECKLIST.md](deploy/DEPLOY-CHECKLIST.md)** - Quick reference checklist
- **[secrets/README.md](secrets/README.md)** - Google Drive setup

## 🎯 Features

✅ **Upload videos** - Drag & drop raw footage  
✅ **Auto-detection** - AI finds trick moments  
✅ **Tinder-style sorting** - Swipe through clips efficiently  
✅ **Precision trimming** - Frame-by-frame control  
✅ **Auto-tagging** - Person, trick, camera, FPS all captured  
✅ **Google Drive sync** - Organized folder structure  
✅ **Searchable filenames** - Find clips instantly  
✅ **Background processing** - Workers handle video processing  
✅ **24/7 uptime** - Deployed on Google Cloud  

## 🗂️ File Naming Schema

```
YYYY-MM-DD__Session__Person__Trick__CAMID__FPS__v###.mp4
```

Example:
```
2024-12-01__BackyardRails__Miller_Downey__KFED__CAM_GOPRO11__240FPS__v001.mp4
```

**Searchable by:** date, session, person, trick, camera, FPS

## 🔒 Security

- Cloudflare Tunnel (encrypted, no open ports)
- SSL/TLS automatic via Cloudflare
- Secrets gitignored
- Service account for Google Drive

## 🛠️ Maintenance

### Update code on server
```bash
# copy changes to VM
gcloud compute scp --recurse backend/ trickyclip-server:/opt/trickyclip/backend/ --zone=YOUR_ZONE

# rebuild on VM
cd /opt/trickyclip/deploy
docker-compose up -d --build
```

### Monitor services
```bash
# check everything
docker-compose ps
sudo systemctl status cloudflared-tunnel

# view logs
docker-compose logs -f worker
sudo journalctl -u cloudflared-tunnel -f
```

## 💰 Cost

- **Development:** FREE (local)
- **Production:** ~$30/month (FREE for ~10 months with Google Cloud credits)

## 📊 Stack

**Frontend:** React + TypeScript + Vite + Tailwind  
**Backend:** FastAPI + Python 3.11  
**Database:** PostgreSQL + Redis  
**Processing:** FFmpeg + RQ Workers  
**Storage:** Local + Google Drive  
**Deployment:** Docker + Google Cloud + Cloudflare Tunnel  

## 🎉 Status

**Production ready!** Deployed at https://trickyclip.com

Contributors: [@Miller-Downey](https://github.com/Miller-Downey)
