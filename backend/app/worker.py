from app.core.db import engine
from sqlmodel import Session, select
from app.models import OriginalFile, CandidateSegment, FinalClip, Person, Trick
from app.services.detection import detect_segments
from app.services.ffmpeg import get_video_metadata
from app.core.config import settings
import os
import subprocess

def analyze_original_file(file_id):
    with Session(engine) as session:
        file = session.get(OriginalFile, file_id)
        if not file:
            return
        
        segments = detect_segments(file.stored_path, file.duration_ms)
        
        for start, end in segments:
            seg = CandidateSegment(
                original_file_id=file.id,
                start_ms=start,
                end_ms=end
            )
            session.add(seg)
        session.commit()

def render_and_upload_clip(final_clip_id):
    with Session(engine) as session:
        clip = session.get(FinalClip, final_clip_id)
        if not clip:
            print(f"FinalClip {final_clip_id} not found")
            return
            
        original = clip.original_file
        
        start_sec = clip.start_ms / 1000.0
        duration_sec = (clip.end_ms - clip.start_ms) / 1000.0
        
        output_path = os.path.join(settings.FINAL_CLIPS_DIR, clip.filename)
        
        # ffmpeg -ss {start_sec} -i /data/originals/<file> -to {duration} -c copy /data/final_clips/<filename>
        # Note: -t is duration, -to is position. Spec used -to {duration} which is likely wrong if start_ss is input option. 
        # If -ss is before -i, -t is duration.
        # Let's use -ss before -i and -t duration for precision.
        
        cmd = [
            "ffmpeg",
            "-ss", str(start_sec),
            "-i", original.stored_path,
            "-t", str(duration_sec),
            "-c", "copy",
            "-y", # overwrite
            output_path
        ]
        
        print(f"Rendering clip: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # In Milestone 1: No drive upload, just local.
            print(f"Rendered to {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error rendering clip: {e.stderr}")

if __name__ == "__main__":
    from redis import Redis
    from rq import Worker, Queue
    
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(connection=redis_conn)
    
    print(f"Starting RQ worker, listening on queue: {queue.name}")
    worker = Worker([queue], connection=redis_conn)
    worker.work()

