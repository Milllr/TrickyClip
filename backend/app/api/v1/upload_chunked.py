from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from sqlmodel import Session
from app.core.db import get_session
from app.core.config import settings
from app.models import OriginalFile
from app.services.ffmpeg import get_video_metadata
from app.services.queue import enqueue_job
from app.worker import analyze_original_file
import os
import hashlib
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

router = APIRouter()

# temporary storage for upload chunks
UPLOAD_TEMP_DIR = os.path.join(settings.DATA_DIR, "uploads_temp")
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)

from pydantic import BaseModel

class InitUploadRequest(BaseModel):
    filename: str
    total_size: int
    chunk_size: int = 5 * 1024 * 1024

@router.post("/init")
def init_chunked_upload(
    req: InitUploadRequest,
    session: Session = Depends(get_session)
):
    """initialize a chunked upload session"""
    upload_id = str(uuid4())
    upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # store metadata
    meta_path = os.path.join(upload_dir, "metadata.txt")
    with open(meta_path, "w") as f:
        f.write(f"filename={req.filename}\n")
        f.write(f"total_size={req.total_size}\n")
        f.write(f"chunk_size={req.chunk_size}\n")
        f.write(f"created_at={datetime.utcnow().isoformat()}\n")
    
    total_chunks = (req.total_size + req.chunk_size - 1) // req.chunk_size
    
    return {
        "upload_id": upload_id,
        "total_chunks": total_chunks,
        "chunk_size": req.chunk_size
    }

@router.post("/chunk/{upload_id}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    chunk: UploadFile = File(...)
):
    """upload a single chunk"""
    upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
    
    if not os.path.exists(upload_dir):
        raise HTTPException(status_code=404, detail="upload session not found")
    
    # save chunk
    chunk_path = os.path.join(upload_dir, f"chunk_{chunk_index:05d}")
    with open(chunk_path, "wb") as f:
        content = await chunk.read()
        f.write(content)
    
    return {
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "status": "received"
    }

@router.post("/complete/{upload_id}")
def complete_chunked_upload(
    upload_id: str,
    session: Session = Depends(get_session)
):
    """finalize chunked upload by combining chunks"""
    upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
    
    if not os.path.exists(upload_dir):
        raise HTTPException(status_code=404, detail="upload session not found")
    
    # read metadata
    meta_path = os.path.join(upload_dir, "metadata.txt")
    metadata = {}
    with open(meta_path, "r") as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            metadata[key] = value
    
    filename = metadata["filename"]
    
    # combine chunks
    temp_file_path = os.path.join(UPLOAD_TEMP_DIR, f"{upload_id}_combined")
    
    chunk_files = sorted([
        f for f in os.listdir(upload_dir) 
        if f.startswith("chunk_")
    ])
    
    with open(temp_file_path, "wb") as output:
        for chunk_file in chunk_files:
            chunk_path = os.path.join(upload_dir, chunk_file)
            with open(chunk_path, "rb") as chunk:
                output.write(chunk.read())
    
    # compute hash
    sha256_hash = hashlib.sha256()
    with open(temp_file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    file_hash = sha256_hash.hexdigest()
    
    # move to final path
    ext = os.path.splitext(filename)[1]
    final_filename = f"{file_hash}{ext}"
    final_path = os.path.join(settings.ORIGINALS_DIR, final_filename)
    
    if not os.path.exists(final_path):
        os.rename(temp_file_path, final_path)
    else:
        os.remove(temp_file_path)
    
    # check if exists in DB
    existing = session.query(OriginalFile).filter(OriginalFile.file_hash == file_hash).first()
    if existing:
        # cleanup temp directory
        shutil.rmtree(upload_dir, ignore_errors=True)
        return {"message": "file already exists", "id": existing.id}
    
    # extract metadata
    try:
        meta = get_video_metadata(final_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid video file: {str(e)}")
    
    # create DB entry
    db_file = OriginalFile(
        original_filename=filename,
        stored_path=final_path,
        file_hash=file_hash,
        camera_id="CAM_UNKNOWN",
        fps_label=f"{int(meta['fps'])}FPS",
        fps=meta['fps'],
        duration_ms=meta['duration_ms'],
        width=meta.get('width', 0),
        height=meta.get('height', 0),
        aspect_ratio=meta.get('aspect_ratio', 'unknown'),
        resolution_label=meta.get('resolution_label', 'unknown'),
        processing_status="pending",
        recorded_at=datetime.utcnow()
    )
    
    if meta.get("creation_time"):
        try:
            db_file.recorded_at = datetime.fromisoformat(meta["creation_time"].replace("Z", "+00:00"))
        except:
            pass
    
    session.add(db_file)
    session.commit()
    session.refresh(db_file)
    
    # enqueue analysis
    enqueue_job(analyze_original_file, db_file.id, file_id=db_file.id)
    
    # cleanup temp directory
    import shutil
    shutil.rmtree(upload_dir, ignore_errors=True)
    
    return {"id": db_file.id, "status": "uploaded"}

@router.get("/status/{upload_id}")
def get_upload_status(upload_id: str):
    """check status of chunked upload"""
    upload_dir = os.path.join(UPLOAD_TEMP_DIR, upload_id)
    
    if not os.path.exists(upload_dir):
        return {"status": "not_found"}
    
    chunk_files = [f for f in os.listdir(upload_dir) if f.startswith("chunk_")]
    
    return {
        "upload_id": upload_id,
        "status": "in_progress",
        "chunks_received": len(chunk_files)
    }

