from app.core.db import engine
from sqlmodel import Session, select
from app.models import OriginalFile, CandidateSegment, FinalClip, Person, Trick
from app.services.detection import detect_segments
from app.services.detection_ml import detect_segments_smart
from app.services.ffmpeg import get_video_metadata
from app.services.drive import drive_service
from app.services.drive_sync import drive_sync
from app.services.job_tracker import start_job, complete_job, fail_job, update_job_progress
from app.core.config import settings
import os
import subprocess
from datetime import datetime
from rq import get_current_job

def analyze_original_file(file_id):
    # get current RQ job for tracking
    current_job = get_current_job()
    
    with Session(engine) as session:
        file = session.get(OriginalFile, file_id)
        if not file:
            return
        
        try:
            # track job start
            if current_job:
                start_job(current_job.id)
            
            # update status to analyzing
            file.processing_status = "analyzing"
            file.analysis_progress_percent = 10
            session.add(file)
            session.commit()
            
            if current_job:
                update_job_progress(current_job.id, 10)
            
            # detect segments using ML motion detection
            print(f"starting ML detection for {file.original_filename}")
            segments_with_scores = detect_segments_smart(file.stored_path, file.duration_ms)
            print(f"ml detection returned {len(segments_with_scores)} segments")
            
            file.analysis_progress_percent = 70
            session.add(file)
            session.commit()
            
            if current_job:
                update_job_progress(current_job.id, 70)
            
            # create candidate segments with confidence scores
            print(f"creating {len(segments_with_scores)} candidate segments in database")
            for start, end, confidence in segments_with_scores:
                seg = CandidateSegment(
                    original_file_id=file.id,
                    start_ms=start,
                    end_ms=end,
                    confidence_score=confidence,
                    detection_method="motion"
                )
                session.add(seg)
            
            print(f"segments added to session, committing...")
            
            # mark as completed
            file.processing_status = "completed"
            file.analysis_progress_percent = 100
            session.add(file)
            session.commit()
            print(f"analyzed file {file_id}: found {len(segments_with_scores)} segments")
            
            # track job completion
            if current_job:
                complete_job(current_job.id)
            
            # if file came from drive (has drive_file_id), move to processed folder
            if hasattr(file, 'drive_file_id') and file.drive_file_id:
                print(f"moving raw video to processed folder in drive")
                drive_sync.move_to_processed_folder(
                    file.drive_file_id,
                    file.original_filename,
                    file.recorded_at
                )
            
            # NOTE: do NOT delete original file here, it is needed for sorting
            # cleanup will happen via StorageManager LRU eviction
            
        except Exception as e:
            # mark as failed
            file.processing_status = "failed"
            session.add(file)
            session.commit()
            print(f"error analyzing file {file_id}: {e}")
            
            # track job failure
            if current_job:
                fail_job(current_job.id, str(e))
            raise

def render_and_upload_clip(final_clip_id):
    # get current RQ job for tracking
    current_job = get_current_job()
    
    with Session(engine) as session:
        try:
            # track job start
            if current_job:
                start_job(current_job.id)
                update_job_progress(current_job.id, 10)
            
            clip = session.get(FinalClip, final_clip_id)
            if not clip:
                print(f"FinalClip {final_clip_id} not found")
                return
                
            original = clip.original_file
            
            start_sec = clip.start_ms / 1000.0
            duration_sec = (clip.end_ms - clip.start_ms) / 1000.0
            
            output_path = os.path.join(settings.FINAL_CLIPS_DIR, clip.filename)
            
            # render clip using ffmpeg
            cmd = [
                "ffmpeg",
                "-ss", str(start_sec),
                "-i", original.stored_path,
                "-t", str(duration_sec),
                "-c", "copy",
                "-y",
                output_path
            ]
            
            print(f"rendering clip: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"rendered to {output_path}")
            
            if current_job:
                update_job_progress(current_job.id, 50)
            
            # upload to google drive
            year = clip.date.strftime("%Y")
            date_description = f"{clip.date.strftime('%Y-%m-%d')}_{clip.session_name}"
            
            person = session.get(Person, clip.person_id) if clip.person_id else None
            trick = session.get(Trick, clip.trick_id) if clip.trick_id else None
            
            person_slug = person.slug if person else "BROLL"
            trick_name = trick.name if trick else "BROLL"
            
            # verify file exists before upload
            if not os.path.exists(output_path):
                raise Exception(f"rendered file not found: {output_path}")
            
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"uploading clip to drive: {clip.filename} ({file_size_mb:.2f} MB)")
            print(f"  year: {year}")
            print(f"  date: {date_description}")
            print(f"  person: {person_slug}")
            print(f"  trick: {trick_name}")
            
            # use small clip upload (non-resumable for small files to avoid quota)
            drive_result = drive_sync.upload_small_clip(
                local_path=output_path,
                year=year,
                date_description=date_description,
                person_slug=person_slug,
                trick_name=trick_name,
                filename=clip.filename
            )
            
            if current_job:
                update_job_progress(current_job.id, 90)
            
            if drive_result:
                clip.drive_file_id = drive_result['drive_file_id']
                clip.drive_url = drive_result['drive_url']
                clip.is_uploaded_to_drive = True
                session.add(clip)
                session.commit()
                print(f"✅ uploaded to drive successfully!")
                print(f"   file id: {drive_result['drive_file_id']}")
                print(f"   url: {drive_result['drive_url']}")
                
                # delete local file to save VM storage
                try:
                    os.remove(output_path)
                    print(f"deleted local file: {output_path}")
                except Exception as e:
                    print(f"warning: could not delete local file: {e}")
            else:
                print("⚠️ drive upload skipped (not configured)")
                raise Exception("drive service not configured")
            
            # track job completion
            if current_job:
                complete_job(current_job.id)
                
        except subprocess.CalledProcessError as e:
            print(f"error rendering clip: {e.stderr}")
            if current_job:
                fail_job(current_job.id, f"ffmpeg error: {e.stderr}")
            raise
        except Exception as e:
            print(f"error in render/upload: {e}")
            if current_job:
                fail_job(current_job.id, str(e))
            raise

def download_and_process_from_drive(drive_file_id: str, filename: str, file_size: int):
    """download video from drive dump folder and queue for analysis"""
    current_job = get_current_job()
    
    with Session(engine) as session:
        try:
            if current_job:
                start_job(current_job.id)
                update_job_progress(current_job.id, 5)
            
            # compute destination path
            import hashlib
            temp_hash = hashlib.md5(f"{drive_file_id}_{filename}".encode()).hexdigest()
            ext = os.path.splitext(filename)[1]
            dest_filename = f"{temp_hash}{ext}"
            dest_path = os.path.join(settings.ORIGINALS_DIR, dest_filename)
            
            # check if already downloaded
            existing = session.query(OriginalFile).filter(
                OriginalFile.drive_file_id == drive_file_id
            ).first()
            
            if existing:
                print(f"video already downloaded: {filename}")
                if current_job:
                    complete_job(current_job.id)
                return
            
            # download from drive
            print(f"downloading {filename} ({file_size / (1024*1024):.2f} MB) from drive...")
            if current_job:
                update_job_progress(current_job.id, 10)
            
            drive_sync.download_video_from_drive(drive_file_id, filename, dest_path)
            
            if current_job:
                update_job_progress(current_job.id, 40)
            
            # extract metadata
            meta = get_video_metadata(dest_path)
            
            # compute file hash for deduplication
            sha256_hash = hashlib.sha256()
            with open(dest_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            file_hash = sha256_hash.hexdigest()
            
            # create database entry
            db_file = OriginalFile(
                original_filename=filename,
                stored_path=dest_path,
                file_hash=file_hash,
                drive_file_id=drive_file_id,
                file_size_bytes=file_size,
                camera_id="CAM_UNKNOWN",
                fps_label=f"{int(meta['fps'])}FPS",
                fps=meta['fps'],
                duration_ms=meta['duration_ms'],
                width=meta.get('width', 0),
                height=meta.get('height', 0),
                aspect_ratio=meta.get('aspect_ratio', 'unknown'),
                resolution_label=meta.get('resolution_label', 'unknown'),
                processing_status="pending",
                recorded_at=datetime.utcnow()
            )
            
            if meta.get("creation_time"):
                try:
                    db_file.recorded_at = datetime.fromisoformat(meta["creation_time"].replace("Z", "+00:00"))
                except:
                    pass
            
            session.add(db_file)
            session.commit()
            session.refresh(db_file)
            
            print(f"downloaded and registered: {filename}")
            
            if current_job:
                update_job_progress(current_job.id, 60)
            
            # queue analysis with extended timeout (video analysis takes time)
            from app.services.queue import enqueue_job
            enqueue_job(analyze_original_file, db_file.id, file_id=db_file.id, timeout='2h')
            
            if current_job:
                complete_job(current_job.id)
            
        except Exception as e:
            print(f"error downloading from drive: {e}")
            if current_job:
                fail_job(current_job.id, str(e))
            raise


if __name__ == "__main__":
    from redis import Redis
    from rq import Worker, Queue
    
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(connection=redis_conn)
    
    print(f"Starting RQ worker, listening on queue: {queue.name}")
    worker = Worker([queue], connection=redis_conn)
    worker.work()

