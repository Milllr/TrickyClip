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
    
    # sync job statuses with RQ registries before returning
    # this catches jobs that were killed or failed without updating the DB
    try:
        failed_registry = FailedJobRegistry(queue=queue)
        finished_registry = FinishedJobRegistry(queue=queue)
        started_registry = StartedJobRegistry(queue=queue)
        
        # get all "running" jobs from DB and check if they're actually still running
        running_db_jobs = session.exec(select(JobModel).where(JobModel.status == "running")).all()
        for db_job in running_db_jobs:
            rq_job_id = db_job.rq_job_id
            
            # check if this job is actually in the failed registry
            if rq_job_id in failed_registry.get_job_ids():
                try:
                    rq_job = Job.fetch(rq_job_id, connection=redis_conn)
                    error_msg = str(rq_job.exc_info) if rq_job.exc_info else "job failed unexpectedly"
                    db_job.status = "failed"
                    db_job.error_message = error_msg[:500]  # truncate if too long
                    db_job.finished_at = datetime.utcnow()
                    session.add(db_job)
                    print(f"synced failed job: {rq_job_id}")
                except:
                    pass
            
            # check if it's in the finished registry but DB still says running
            elif rq_job_id in finished_registry.get_job_ids():
                db_job.status = "completed"
                db_job.finished_at = datetime.utcnow()
                db_job.progress_percent = 100
                session.add(db_job)
                print(f"synced completed job: {rq_job_id}")
            
            # check if it's not in started registry anymore (killed/lost)
            elif rq_job_id not in started_registry.get_job_ids():
                try:
                    rq_job = Job.fetch(rq_job_id, connection=redis_conn)
                    # if we can fetch it but it's not in any registry, it was likely killed
                    if rq_job.is_failed:
                        db_job.status = "failed"
                        db_job.error_message = "worker killed or job timeout exceeded"
                        db_job.finished_at = datetime.utcnow()
                        session.add(db_job)
                        print(f"marked killed job as failed: {rq_job_id}")
                except:
                    # job doesn't exist in RQ anymore, mark as failed
                    db_job.status = "failed"
                    db_job.error_message = "job lost (not found in queue)"
                    db_job.finished_at = datetime.utcnow()
                    session.add(db_job)
                    print(f"marked lost job as failed: {rq_job_id}")
        
        session.commit()
    except Exception as e:
        print(f"error syncing job statuses: {e}")
        # continue anyway, just use DB state as-is
    
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

