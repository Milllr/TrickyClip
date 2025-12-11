from sqlmodel import Session
from app.core.db import engine
from app.models import Job
from datetime import datetime
from uuid import UUID
from typing import Optional

def create_job_record(rq_job_id: str, job_type: str, file_id: Optional[UUID] = None, clip_id: Optional[UUID] = None) -> UUID:
    """create a job record in the database when a job is queued"""
    with Session(engine) as session:
        job = Job(
            rq_job_id=rq_job_id,
            job_type=job_type,
            status="queued",
            file_id=file_id,
            clip_id=clip_id
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id

def start_job(rq_job_id: str):
    """mark a job as started"""
    with Session(engine) as session:
        job = session.query(Job).filter(Job.rq_job_id == rq_job_id).first()
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            session.add(job)
            session.commit()

def update_job_progress(rq_job_id: str, progress_percent: int):
    """update job progress"""
    with Session(engine) as session:
        job = session.query(Job).filter(Job.rq_job_id == rq_job_id).first()
        if job:
            job.progress_percent = progress_percent
            job.updated_at = datetime.utcnow()
            session.add(job)
            session.commit()

def complete_job(rq_job_id: str):
    """mark a job as completed"""
    with Session(engine) as session:
        job = session.query(Job).filter(Job.rq_job_id == rq_job_id).first()
        if job:
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            job.progress_percent = 100
            job.updated_at = datetime.utcnow()
            session.add(job)
            session.commit()

def fail_job(rq_job_id: str, error_message: str):
    """mark a job as failed"""
    with Session(engine) as session:
        job = session.query(Job).filter(Job.rq_job_id == rq_job_id).first()
        if job:
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            job.error_message = error_message
            job.updated_at = datetime.utcnow()
            session.add(job)
            session.commit()



