from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlmodel import Session
from app.core.db import get_session
from app.core.config import settings
from app.models import OriginalFile
from app.services.ffmpeg import get_video_metadata
from app.services.queue import enqueue_job
from app.worker import analyze_original_file
import shutil
import os
import hashlib
from datetime import datetime

router = APIRouter()

@router.post("/")
async def upload_file(
    file: UploadFile = File(...), 
    session: Session = Depends(get_session)
):
    # Save to temp
    temp_path = os.path.join(settings.ORIGINALS_DIR, f"temp_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Compute hash
    sha256_hash = hashlib.sha256()
    with open(temp_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    file_hash = sha256_hash.hexdigest()
    
    # Move to final path
    ext = os.path.splitext(file.filename)[1]
    final_filename = f"{file_hash}{ext}"
    final_path = os.path.join(settings.ORIGINALS_DIR, final_filename)
    
    if not os.path.exists(final_path):
        shutil.move(temp_path, final_path)
    else:
        os.remove(temp_path) # duplicate
        
    # Check if exists in DB
    existing = session.query(OriginalFile).filter(OriginalFile.file_hash == file_hash).first()
    if existing:
        return {"message": "File already exists", "id": existing.id}
        
    # Extract metadata
    try:
        meta = get_video_metadata(final_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")
        
    # Create DB entry
    db_file = OriginalFile(
        original_filename=file.filename,
        stored_path=final_path,
        file_hash=file_hash,
        camera_id="CAM_UNKNOWN", # Placeholder or map from meta
        fps_label=f"{int(meta['fps'])}FPS",
        fps=meta['fps'],
        duration_ms=meta['duration_ms'],
        recorded_at=datetime.utcnow() # Placeholder if meta doesn't have creation_time
    )
    
    if meta.get("creation_time"):
        try:
            # simple parse, might need robust parsing for ISO
            db_file.recorded_at = datetime.fromisoformat(meta["creation_time"].replace("Z", "+00:00"))
        except:
            pass
            
    session.add(db_file)
    session.commit()
    session.refresh(db_file)
    
    # Enqueue analysis
    enqueue_job(analyze_original_file, db_file.id)
    
    return {"id": db_file.id, "status": "uploaded"}

