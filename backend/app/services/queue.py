from redis import Redis
from rq import Queue
from app.core.config import settings
from app.services.job_tracker import create_job_record
from typing import Optional
from uuid import UUID

redis_conn = Redis.from_url(settings.REDIS_URL)
queue = Queue(connection=redis_conn)

def enqueue_job(func, *args, file_id: Optional[UUID] = None, clip_id: Optional[UUID] = None, **kwargs):
    """enqueue a job and track it in the database"""
    rq_job = queue.enqueue(func, *args, **kwargs)
    
    # determine job type from function name
    job_type = func.__name__
    
    # create database record
    create_job_record(
        rq_job_id=rq_job.id,
        job_type=job_type,
        file_id=file_id,
        clip_id=clip_id
    )
    
    return rq_job

