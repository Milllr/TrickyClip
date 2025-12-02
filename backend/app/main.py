from fastapi import FastAPI
from app.core.db import init_db
from app.api.v1 import upload, sort, people, tricks # will create these
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

app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(sort.router, prefix="/api/sort", tags=["sort"])
app.include_router(people.router, prefix="/api/people", tags=["people"])
app.include_router(tricks.router, prefix="/api/tricks", tags=["tricks"])

