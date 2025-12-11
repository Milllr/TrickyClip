from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from app.core.db import get_session, engine
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

@router.get("/detection-debug/{file_id}")
def get_detection_debug(file_id: UUID, session: Session = Depends(get_session)):
    """
    debug endpoint for detection pipeline
    returns motion/audio timeseries and detected segments
    """
    from app.models import OriginalFile, CandidateSegment
    from app.video.proxy_utils import generate_proxy_video
    from app.detection.stage1_motion import compute_motion_energy_timeseries
    from app.detection.stage1_audio import compute_audio_energy_timeseries
    from app.detection.stage1_candidates import find_candidate_windows
    from app.detection.config import DetectionConfig
    
    try:
        # get file
        file = session.get(OriginalFile, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="file not found")
        
        # generate proxy
        proxy_path = generate_proxy_video(file.stored_path)
        
        # compute timeseries
        motion_times, motion_energy = compute_motion_energy_timeseries(proxy_path)
        audio_times, audio_energy = compute_audio_energy_timeseries(proxy_path)
        
        # get candidate windows
        config = DetectionConfig()
        candidate_windows = find_candidate_windows(
            motion_times, motion_energy,
            audio_times, audio_energy,
            config
        )
        
        # get actual segments from db
        segments = session.exec(
            select(CandidateSegment)
            .where(CandidateSegment.original_file_id == file_id)
            .order_by(CandidateSegment.start_ms)
        ).all()
        
        # downsample timeseries for response (every 10th sample)
        motion_downsampled = {
            "times": motion_times[::10].tolist() if len(motion_times) > 0 else [],
            "energy": motion_energy[::10].tolist() if len(motion_energy) > 0 else []
        }
        
        audio_downsampled = {
            "times": audio_times[::10].tolist() if len(audio_times) > 0 else [],
            "energy": audio_energy[::10].tolist() if len(audio_energy) > 0 else []
        }
        
        return {
            "file_id": str(file_id),
            "filename": file.original_filename,
            "duration_sec": file.duration_ms / 1000.0,
            "motion_timeseries": motion_downsampled,
            "audio_timeseries": audio_downsampled,
            "stage1_windows": [
                {
                    "start_sec": w.start_sec,
                    "end_sec": w.end_sec,
                    "motion_score": w.motion_score,
                    "audio_score": w.audio_score,
                    "combined_score": w.combined_score
                }
                for w in candidate_windows
            ],
            "final_segments": [
                {
                    "id": str(seg.id),
                    "start_sec": seg.start_ms / 1000.0,
                    "end_sec": seg.end_ms / 1000.0,
                    "confidence": seg.confidence_score,
                    "method": seg.detection_method,
                    "status": seg.status
                }
                for seg in segments
            ],
            "config": {
                "motion_threshold": config.motion_threshold,
                "audio_threshold": config.audio_threshold,
                "ml_threshold": config.ml_threshold,
                "use_stage1": config.use_stage1,
                "use_ml_stage2": config.use_ml_stage2
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

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

@router.post("/generate-proxies")
def generate_missing_proxies(session: Session = Depends(get_session)):
    """
    Queue background jobs to generate playback proxies for all videos that don't have them.
    Returns immediately with job IDs.
    """
    from app.models import OriginalFile
    from pathlib import Path
    import os
    
    try:
        # Get all original files
        files = session.exec(select(OriginalFile)).all()
        
        results = {
            "total_videos": len(files),
            "jobs_queued": 0,
            "proxies_exist": 0,
            "skipped": []
        }
        
        for file in files:
            if not os.path.exists(file.stored_path):
                results["skipped"].append({
                    "file_id": str(file.id),
                    "reason": "Original file not found"
                })
                continue
            
            # Check if proxy already exists
            input_path_obj = Path(file.stored_path)
            proxy_filename = input_path_obj.stem + "_web.mp4"
            proxy_dir = Path(os.getenv("DATA_DIR", "/data")) / "playback_proxies"
            proxy_path = proxy_dir / proxy_filename
            
            if proxy_path.exists():
                results["proxies_exist"] += 1
                continue
            
            # Queue background job to generate proxy
            job = enqueue_job(
                generate_proxy_for_file,
                str(file.id),
                file_id=file.id,
                timeout='1h'
            )
            results["jobs_queued"] += 1
            print(f"Queued proxy generation for {file.original_filename} (job {job.id})")
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_proxy_for_file(file_id_str: str):
    """Background worker job to generate a playback proxy for a single file"""
    from app.models import OriginalFile
    from app.video.proxy_utils import generate_playback_proxy
    from uuid import UUID
    import os
    
    with Session(engine) as session:
        file = session.get(OriginalFile, UUID(file_id_str))
        if not file:
            print(f"File {file_id_str} not found")
            return
        
        if not os.path.exists(file.stored_path):
            print(f"Original file not found: {file.stored_path}")
            return
        
        try:
            print(f"[PROXY] Generating playback proxy for: {file.original_filename}")
            proxy_path = generate_playback_proxy(file.stored_path, max_height=1080)
            print(f"[PROXY] ✅ Success: {proxy_path}")
        except Exception as e:
            print(f"[PROXY] ❌ Failed for {file.original_filename}: {e}")
            import traceback
            traceback.print_exc()
            raise


@router.get("/system-stats")
def get_system_stats():
    """Get real-time system statistics"""
    import psutil
    import shutil
    from app.core.config import settings
    from datetime import datetime
    
    try:
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = shutil.disk_usage(settings.DATA_DIR)
        
        # Container stats (basic - would need docker socket for real status)
        containers_status = {
            "backend": "running",
            "worker": "running",
            "frontend": "running",
            "drive-sync": "running",
            "db": "running",
            "redis": "running"
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "containers": containers_status
        }
    except Exception as e:
        print(f"Error getting system stats: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": 0,
            "memory": {"total": 0, "available": 0, "percent": 0, "used": 0},
            "disk": {"total": 0, "used": 0, "free": 0, "percent": 0},
            "containers": {}
        }
