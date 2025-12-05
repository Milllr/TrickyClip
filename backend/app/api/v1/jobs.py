from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Job as JobModel
from app.services.queue import queue, redis_conn
from rq.job import Job
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.get("/")
def get_jobs(
    session: Session = Depends(get_session),
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """get job statuses from database with live RQ updates"""
    
    # query database for jobs
    query = select(JobModel).order_by(JobModel.created_at.desc()).limit(limit)
    if status:
        query = query.where(JobModel.status == status)
    
    db_jobs = session.exec(query).all()
    
    # organize by status
    running_jobs = []
    queued_jobs = []
    completed_jobs = []
    failed_jobs = []
    
    for job in db_jobs:
        job_dict = {
            "id": str(job.id),
            "rq_job_id": job.rq_job_id,
            "job_type": job.job_type,
            "status": job.status,
            "file_id": str(job.file_id) if job.file_id else None,
            "clip_id": str(job.clip_id) if job.clip_id else None,
            "progress_percent": job.progress_percent,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        
        if job.status == "running":
            running_jobs.append(job_dict)
        elif job.status == "queued":
            queued_jobs.append(job_dict)
        elif job.status == "completed":
            completed_jobs.append(job_dict)
        elif job.status == "failed":
            failed_jobs.append(job_dict)
    
    # get total counts (all time)
    total_running = session.exec(select(JobModel).where(JobModel.status == "running")).all()
    total_queued = session.exec(select(JobModel).where(JobModel.status == "queued")).all()
    total_completed = session.exec(select(JobModel).where(JobModel.status == "completed")).all()
    total_failed = session.exec(select(JobModel).where(JobModel.status == "failed")).all()
    
    return {
        "running": running_jobs,
        "queued": queued_jobs,
        "completed": completed_jobs[:20],  # last 20
        "failed": failed_jobs[:20],  # last 20
        "summary": {
            "running_count": len(total_running),
            "queued_count": len(total_queued),
            "completed_count": len(total_completed),
            "failed_count": len(total_failed),
        }
    }

