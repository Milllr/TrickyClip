import logging
from typing import Callable, Any
from functools import wraps
import time

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    decorator to retry a function with exponential backoff
    
    usage:
        @retry_with_backoff(max_retries=5, initial_delay=2.0)
        def upload_to_drive(file_path):
            # ... code that might fail ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                            f"retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {str(e)}"
                        )
            
            # all retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


def handle_worker_error(job_id: str, error: Exception):
    """
    centralized error handler for worker jobs
    logs error and optionally sends notifications
    """
    logger.error(f"job {job_id} failed: {error}", exc_info=True)
    
    # future: send slack/email notifications
    # send_slack_notification(f"Job failed: {job_id}\nError: {str(error)}")
    
    # future: add to dead letter queue for manual review
    # add_to_dlq(job_id, error)


class TrickyClipException(Exception):
    """base exception for trickyclip-specific errors"""
    pass


class VideoProcessingError(TrickyClipException):
    """raised when video processing fails"""
    pass


class DriveUploadError(TrickyClipException):
    """raised when drive upload fails"""
    pass


class DetectionError(TrickyClipException):
    """raised when segment detection fails"""
    pass


