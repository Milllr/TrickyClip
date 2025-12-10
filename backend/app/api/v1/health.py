from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.services.queue import redis_conn
from app.services.drive import drive_service
from app.models import OriginalFile
import time
from datetime import datetime

router = APIRouter()

@router.get("/")
def health_check():
    """basic liveness check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "trickyclip-backend"
    }

@router.get("/ready")
def readiness_check(session: Session = Depends(get_session)):
    """comprehensive readiness check - verifies all dependencies"""
    checks = {}
    all_healthy = True
    
    # check database
    try:
        session.exec(select(OriginalFile).limit(1))
        checks["database"] = {"status": "healthy", "message": "connected"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": str(e)}
        all_healthy = False
    
    # check redis
    try:
        redis_conn.ping()
        checks["redis"] = {"status": "healthy", "message": "connected"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "message": str(e)}
        all_healthy = False
    
    # check google drive
    try:
        if drive_service.service:
            checks["google_drive"] = {"status": "healthy", "message": "configured"}
        else:
            checks["google_drive"] = {"status": "warning", "message": "not configured"}
    except Exception as e:
        checks["google_drive"] = {"status": "unhealthy", "message": str(e)}
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }

@router.get("/metrics")
def get_metrics(session: Session = Depends(get_session)):
    """prometheus-style metrics"""
    from app.models import Job, FinalClip, CandidateSegment
    
    # count various entities
    total_files = len(session.exec(select(OriginalFile)).all())
    total_segments = len(session.exec(select(CandidateSegment)).all())
    total_clips = len(session.exec(select(FinalClip)).all())
    
    # job metrics
    jobs_running = len(session.exec(select(Job).where(Job.status == "running")).all())
    jobs_queued = len(session.exec(select(Job).where(Job.status == "queued")).all())
    jobs_completed = len(session.exec(select(Job).where(Job.status == "completed")).all())
    jobs_failed = len(session.exec(select(Job).where(Job.status == "failed")).all())
    
    # processing status
    files_pending = len(session.exec(select(OriginalFile).where(OriginalFile.processing_status == "pending")).all())
    files_analyzing = len(session.exec(select(OriginalFile).where(OriginalFile.processing_status == "analyzing")).all())
    files_completed = len(session.exec(select(OriginalFile).where(OriginalFile.processing_status == "completed")).all())
    files_failed = len(session.exec(select(OriginalFile).where(OriginalFile.processing_status == "failed")).all())
    
    # clip metrics
    clips_uploaded = len(session.exec(select(FinalClip).where(FinalClip.is_uploaded_to_drive == True)).all())
    clips_pending = total_clips - clips_uploaded
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "files": {
            "total": total_files,
            "pending": files_pending,
            "analyzing": files_analyzing,
            "completed": files_completed,
            "failed": files_failed
        },
        "segments": {
            "total": total_segments
        },
        "clips": {
            "total": total_clips,
            "uploaded": clips_uploaded,
            "pending_upload": clips_pending
        },
        "jobs": {
            "running": jobs_running,
            "queued": jobs_queued,
            "completed": jobs_completed,
            "failed": jobs_failed
        }
    }


