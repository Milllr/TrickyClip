from fastapi import FastAPI
from app.core.db import init_db
from app.api.v1 import upload, sort, people, tricks, jobs, clips, health, admin, ws, auth, videos, locations, cameras
from app.core.config import settings
import os

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    init_db()
    os.makedirs(settings.ORIGINALS_DIR, exist_ok=True)
    os.makedirs(settings.CANDIDATES_DIR, exist_ok=True)
    os.makedirs(settings.FINAL_CLIPS_DIR, exist_ok=True)
    os.makedirs(settings.PLAYBACK_PROXIES_DIR, exist_ok=True)
    
    # publish startup log
    try:
        from app.services.log_publisher import publish_log
        publish_log('backend', 'SUCCESS', '🚀 trickyclip backend online - all systems operational')
    except Exception as e:
        print(f"failed to publish startup log: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to TrickyClip API"}

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(sort.router, prefix="/api/sort", tags=["sort"])
app.include_router(people.router, prefix="/api/people", tags=["people"])
app.include_router(tricks.router, prefix="/api/tricks", tags=["tricks"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(clips.router, prefix="/api/clips", tags=["clips"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(locations.router, prefix="/api/locations", tags=["locations"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(ws.router, prefix="/ws", tags=["websocket"])

