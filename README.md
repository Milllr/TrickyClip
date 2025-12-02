# TrickyClip

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

### Milestone 1 – Minimal end-to-end skeleton
*   Backend FastAPI + DB (Postgres/SQLite)
*   Models created
*   `/api/upload` endpoint (saves file, extracts metadata, creates dummy segments)
*   `/api/sort/next`, `/api/sort/save`, `/api/sort/trash` implemented
*   `render_and_upload_clip` job (local render only)
*   Frontend `/sort` page (video player, trim sliders, save/trash)
