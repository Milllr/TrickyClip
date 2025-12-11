from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
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
from uuid import UUID

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
        camera_id="CAM_UNKNOWN", # placeholder or map from meta
        fps_label=f"{int(meta['fps'])}FPS",
        fps=meta['fps'],
        duration_ms=meta['duration_ms'],
        width=meta.get('width', 0),
        height=meta.get('height', 0),
        aspect_ratio=meta.get('aspect_ratio', 'unknown'),
        resolution_label=meta.get('resolution_label', 'unknown'),
        recorded_at=datetime.utcnow() # placeholder if meta doesn't have creation_time
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
    
    # enqueue analysis with file_id tracking
    enqueue_job(analyze_original_file, db_file.id, file_id=db_file.id)
    
    return {"id": db_file.id, "status": "uploaded"}

@router.get("/media/{file_id}/info")
def get_media_info(file_id: UUID, session: Session = Depends(get_session)):
    """diagnostic endpoint to check video file status"""
    from app.video.proxy_utils import generate_playback_proxy
    from pathlib import Path
    
    db_file = session.get(OriginalFile, file_id)
    if not db_file:
        return {"error": "File not found in database"}
    
    info = {
        "file_id": str(file_id),
        "original_filename": db_file.original_filename,
        "stored_path": db_file.stored_path,
        "original_exists": os.path.exists(db_file.stored_path),
    }
    
    if info["original_exists"]:
        info["original_size"] = os.path.getsize(db_file.stored_path)
        
        # Check what proxy would be generated
        input_path_obj = Path(db_file.stored_path)
        proxy_filename = input_path_obj.stem + "_web.mp4"
        proxy_dir = Path(os.getenv("DATA_DIR", "/data")) / "playback_proxies"
        proxy_path = proxy_dir / proxy_filename
        
        info["proxy_path"] = str(proxy_path)
        info["proxy_exists"] = proxy_path.exists()
        if info["proxy_exists"]:
            info["proxy_size"] = proxy_path.stat().st_size
    
    return info

@router.get("/media/{file_id}")
def get_media(file_id: UUID, session: Session = Depends(get_session)):
    """serve video file for playback (with browser-compatible proxy)"""
    from app.video.proxy_utils import generate_playback_proxy
    import logging
    
    logger = logging.getLogger(__name__)
    
    db_file = session.get(OriginalFile, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(db_file.stored_path):
        logger.error(f"Original file not found on disk: {db_file.stored_path}")
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    try:
        # Generate/use playback proxy (this is synchronous and will wait)
        logger.info(f"Generating proxy for: {db_file.stored_path}")
        proxy_path = generate_playback_proxy(db_file.stored_path, max_height=1080)
        
        # Verify proxy exists
        if not os.path.exists(proxy_path):
            logger.error(f"Proxy generation failed, file doesn't exist: {proxy_path}")
            raise HTTPException(status_code=500, detail="Failed to generate playback proxy")
        
        # Verify proxy has content
        file_size = os.path.getsize(proxy_path)
        if file_size == 0:
            logger.error(f"Proxy file is empty: {proxy_path}")
            raise HTTPException(status_code=500, detail="Playback proxy is empty")
        
        logger.info(f"Serving proxy: {proxy_path} ({file_size} bytes)")
        
        # Always serve as video/mp4 since we generate MP4
        return FileResponse(
            proxy_path,
            media_type="video/mp4",
            filename=db_file.original_filename
        )
        
    except Exception as e:
        logger.error(f"Error serving video {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error serving video: {str(e)}")

