from fastapi import FastAPI
from app.core.db import init_db
from app.api.v1 import upload, sort, people, tricks, jobs, clips, health, admin, upload_chunked, ws
from app.core.config import settings
import os

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    init_db()
    os.makedirs(settings.ORIGINALS_DIR, exist_ok=True)
    os.makedirs(settings.CANDIDATES_DIR, exist_ok=True)
    os.makedirs(settings.FINAL_CLIPS_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Welcome to TrickyClip API"}

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(upload_chunked.router, prefix="/api/upload-chunked", tags=["upload"])
app.include_router(sort.router, prefix="/api/sort", tags=["sort"])
app.include_router(people.router, prefix="/api/people", tags=["people"])
app.include_router(tricks.router, prefix="/api/tricks", tags=["tricks"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(clips.router, prefix="/api/clips", tags=["clips"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ws.router, prefix="/ws", tags=["websocket"])

