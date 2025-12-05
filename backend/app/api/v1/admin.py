from fastapi import APIRouter, HTTPException
from app.services.storage_manager import storage_manager
from app.services.drive_sync import drive_sync
from app.services.queue import enqueue_job
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CleanupRequest(BaseModel):
    aggressive: bool = False

@router.get("/storage")
def get_storage_stats():
    """get current storage usage statistics"""
    return storage_manager.get_disk_usage()

@router.post("/storage/cleanup")
def trigger_cleanup(request: CleanupRequest):
    """trigger storage cleanup routine"""
    try:
        result = storage_manager.run_cleanup(aggressive=request.aggressive)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reprocess/{file_id}")
def reprocess_file(file_id: str):
    """manually trigger reprocessing of a file"""
    from app.services.queue import enqueue_job
    from app.worker import analyze_original_file
    from uuid import UUID
    
    try:
        file_uuid = UUID(file_id)
        job = enqueue_job(analyze_original_file, file_uuid, file_id=file_uuid)
        return {
            "success": True,
            "job_id": job.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-from-drive")
def sync_from_drive_dump():
    """poll drive dump folder and download new videos for processing"""
    from app.worker import download_and_process_from_drive
    
    try:
        videos = drive_sync.get_new_videos_from_dump()
        
        if not videos:
            return {
                "success": True,
                "message": "no new videos in dump folder",
                "videos_found": 0
            }
        
        # queue download jobs for each video
        jobs_queued = []
        for video in videos:
            job = enqueue_job(
                download_and_process_from_drive,
                video['id'],
                video['name'],
                int(video.get('size', 0))
            )
            jobs_queued.append(job.id)
        
        return {
            "success": True,
            "videos_found": len(videos),
            "jobs_queued": jobs_queued
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

