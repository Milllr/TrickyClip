from redis import Redis
from rq import Queue
from app.core.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)
queue = Queue(connection=redis_conn)

def enqueue_job(func, *args, **kwargs):
    return queue.enqueue(func, *args, **kwargs)

