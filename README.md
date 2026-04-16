# trickyclip

an AI-powered ski/snowboard clip organizer i built to solve a real problem. after a session you end up with hours of GoPro footage and no easy way to find the actual tricks. trickyclip detects trick moments using motion analysis and lets you sort through them tinder-style. accepted clips get auto-organized to google drive with searchable filenames.

*the hosted version ran for ~3 months on a google cloud VM but i took it offline to save on hosting costs (~$30/mo). still runs locally via docker compose.*

## how it works

1. **upload** raw videos to a google drive "dump" folder
2. **sync** triggers download and analysis
3. **detect** - ORB keypoint tracking for camera-stabilized motion, audio energy for impact sounds
4. **sort** - tinder-style UI: swipe through segments, adjust trim points, tag person/trick
5. **render** - FFmpeg renders accepted clips, uploads to drive
6. **organize** - clips land in `Drive/2025/{date}/{person}/{trick}/`

### filename format
```
2025-01-08__BackyardSession__Miller__KFED__CAM_GOPRO11__240FPS__v001.mp4
```

## detection pipeline

- **stage 1:** motion + audio analysis. ORB keypoints + homography, audio energy, candidate window fusion
- **stage 2 (optional):** ML scoring with MoViNet. filters to 5-10 high-confidence segments per video

## stack

**languages:** TypeScript, Python 3.11, SQL

**frameworks:** React, FastAPI, SQLModel + Alembic

**infra:** PostgreSQL, Redis + RQ, Docker Compose, Google Cloud VM, Cloudflare Tunnel

**libraries & API's:** OpenCV, MoViNet, FFmpeg, Vite, Tailwind, Google Drive API

## run locally

```bash
cd deploy
docker compose up -d --build
```

needs a `backend/.env` with database URL, google drive credentials, and OAuth config.

## google drive setup

requires a google cloud service account with drive API access. download the JSON key, share your drive folders with the service account email, configure folder IDs in `.env`. the secrets/ directory is gitignored.
