from app.core.config import settings
import json
from datetime import datetime
from typing import Literal, Optional

# Lazy initialize Redis to avoid startup issues
_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        import redis
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client

LogLevel = Literal['INFO', 'WARNING', 'ERROR', 'SUCCESS', 'DEBUG']
LogSource = Literal['drive-sync', 'worker', 'backend', 'system']

def publish_log(
    source: LogSource,
    level: LogLevel,
    message: str,
    metadata: Optional[dict] = None
):
    """Publish a log message to Redis for real-time streaming"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "source": source,
        "level": level,
        "message": message,
        "metadata": metadata or {}
    }
    
    try:
        redis_client = get_redis_client()
        redis_client.publish('system_logs', json.dumps(log_entry))
    except Exception as e:
        # Don't crash if Redis publish fails - just print
        print(f"Failed to publish log: {e}")

