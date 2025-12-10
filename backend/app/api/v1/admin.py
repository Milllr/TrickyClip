from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from app.core.db import get_session
from app.services.storage_manager import storage_manager
from app.services.drive_sync import drive_sync
from app.services.queue import enqueue_job
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import os

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
    from app.worker import analyze_original_file
    
    try:
        file_uuid = UUID(file_id)
        job = enqueue_job(analyze_original_file, file_uuid, file_id=file_uuid)
        return {
            "success": True,
            "job_id": job.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/archive/{file_id}")
def archive_file(file_id: str, session: Session = Depends(get_session)):
    """manually move file to processed folder and delete local copy"""
    from app.models import OriginalFile
    
    try:
        file = session.get(OriginalFile, UUID(file_id))
        if not file:
            raise HTTPException(status_code=404, detail="file not found")
            
        if not file.drive_file_id:
            raise HTTPException(status_code=400, detail="file not linked to drive")
            
        # move on drive
        drive_sync.move_to_processed_folder(
            file.drive_file_id,
            file.original_filename,
            file.recorded_at
        )
        
        # update status
        file.processing_status = "archived"
        session.add(file)
        session.commit()
        
        # delete local
        if os.path.exists(file.stored_path):
            os.remove(file.stored_path)
            
        return {"success": True, "message": "file archived"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drive-test")
def test_drive_access():
    """test drive api access and folder permissions"""
    from app.services.drive import DriveService
    
    try:
        drive_service = DriveService()
        
        # test: can we access the drive at all?
        about = drive_service.service.about().get(fields="user").execute()
        
        # test: can we see the dump folder?
        dump_id = drive_sync.dump_folder_id
        try:
            folder = drive_service.service.files().get(
                fileId=dump_id,
                fields='id, name, parents, capabilities'
            ).execute()
            folder_accessible = True
            folder_info = folder
        except Exception as e:
            folder_accessible = False
            folder_info = str(e)
        
        # test: can we list files in dump?
        query = f"'{dump_id}' in parents and trashed=false"
        try:
            results = drive_service.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size)',
                pageSize=100
            ).execute()
            files_in_dump = results.get('files', [])
        except Exception as e:
            files_in_dump = f"error: {e}"
        
        return {
            "drive_authenticated": True,
            "service_account": about.get('user', {}).get('emailAddress', 'unknown'),
            "dump_folder_id": dump_id,
            "dump_folder_accessible": folder_accessible,
            "dump_folder_info": folder_info,
            "files_found": files_in_dump
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/sync-from-drive")
def sync_from_drive_dump():
    """poll drive dump folder and download new videos for processing (respecting disk space)"""
    from app.worker import download_and_process_from_drive
    from app.services.queue import queue
    from app.models import OriginalFile
    
    try:
        # debug: check all videos in dump folder
        all_videos = drive_sync.get_new_videos_from_dump()
        print(f"DEBUG: found {len(all_videos)} total videos in dump folder")
        print(f"DEBUG: dump_folder_id = {drive_sync.dump_folder_id}")
        for v in all_videos:
            print(f"  - {v['name']} (id: {v['id']}, size: {v.get('size', 'unknown')})")
        
        # get queue of videos that fit in storage
        videos = drive_sync.get_download_queue()
        print(f"DEBUG: {len(videos)} videos passed queue filters")
        
        if not videos:
            return {
                "success": True,
                "message": "no new videos found or disk full",
                "videos_found": 0,
                "total_in_dump": len(all_videos)
            }
        
        # queue download jobs for each video with extended timeout
        # prevent duplicate jobs by checking both RQ queue and database
        jobs_queued = []
        for video in videos:
            drive_file_id = video['id']
            
            # check if job already queued or running
            existing_job_queued = False
            for job in queue.jobs:
                if job.args and len(job.args) > 0 and job.args[0] == drive_file_id:
                    print(f"DEBUG: job already queued for {video['name']}, skipping")
                    existing_job_queued = True
                    break
            
            if existing_job_queued:
                continue
            
            job = enqueue_job(
                download_and_process_from_drive,
                drive_file_id,
                video['name'],
                int(video.get('size', 0)),
                timeout='2h'
            )
            jobs_queued.append(job.id)
            print(f"DEBUG: queued job {job.id} for {video['name']}")
        
        return {
            "success": True,
            "videos_found": len(videos),
            "jobs_queued": jobs_queued,
            "total_in_dump": len(all_videos)
        }
    except Exception as e:
        print(f"ERROR in sync_from_drive_dump: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
