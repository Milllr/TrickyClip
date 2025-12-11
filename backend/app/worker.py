from app.core.db import engine
from sqlmodel import Session, select
from app.models import OriginalFile, CandidateSegment, FinalClip, Person, Trick
from app.services.ffmpeg import get_video_metadata
from app.services.drive import drive_service
from app.services.drive_sync import drive_sync
from app.services.job_tracker import start_job, complete_job, fail_job, update_job_progress
from app.services.log_publisher import publish_log
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
            
            # check if new detection pipeline is enabled
            # always use stage 1 detection (motion + audio)
            from app.detection.config import DetectionConfig
            config = DetectionConfig()
            
            publish_log('worker', 'INFO', f'🎬 starting analysis: {file.original_filename}')
            print(f"[DETECTION] starting stage 1 detection for {file.original_filename}")
            
            # generate proxy video for efficient analysis
            from app.video.proxy_utils import generate_proxy_video, generate_playback_proxy
            publish_log('worker', 'INFO', '🔄 generating analysis proxy (720p)...')
            proxy_path = generate_proxy_video(file.stored_path)
            
            # ALSO generate playback proxy now (so it's ready for sorting)
            publish_log('worker', 'INFO', '🎥 pre-generating playback proxy for web...')
            print(f"[DETECTION] pre-generating playback proxy for web...")
            try:
                playback_proxy = generate_playback_proxy(file.stored_path, max_height=1080)
                publish_log('worker', 'SUCCESS', f'✅ playback proxy ready: {os.path.basename(playback_proxy)}')
                print(f"[DETECTION] ✅ playback proxy ready: {playback_proxy}")
            except Exception as e:
                publish_log('worker', 'WARNING', f'⚠️  playback proxy generation failed: {str(e)}')
                print(f"[DETECTION] ⚠️ playback proxy generation failed: {e}")
            
            if current_job:
                update_job_progress(current_job.id, 20)
            
            # stage 1: motion + audio analysis
            from app.detection.stage1_motion import compute_motion_energy_timeseries
            from app.detection.stage1_audio import compute_audio_energy_timeseries
            from app.detection.stage1_candidates import find_candidate_windows
            
            publish_log('worker', 'INFO', '📊 analyzing motion patterns (ORB keypoints + homography)...')
            motion_times, motion_energy = compute_motion_energy_timeseries(proxy_path)
            
            if current_job:
                update_job_progress(current_job.id, 40)
            
            publish_log('worker', 'INFO', '🔊 analyzing audio energy (impact detection)...')
            audio_times, audio_energy = compute_audio_energy_timeseries(proxy_path)
            
            if current_job:
                update_job_progress(current_job.id, 50)
            
            candidate_windows = find_candidate_windows(
                motion_times, motion_energy,
                audio_times, audio_energy,
                config
            )
            
            publish_log('worker', 'SUCCESS', f'✅ stage 1 complete: found {len(candidate_windows)} candidate windows')
            print(f"[DETECTION] stage 1 produced {len(candidate_windows)} windows")
            
            # stage 2: ml scoring (if enabled and model available)
            if config.use_ml_stage2:
                from app.detection import get_highlight_model
                
                highlight_model = get_highlight_model()
                
                if highlight_model:
                    print(f"[DETECTION] running stage 2 ml scoring...")
                    
                    filtered_windows = []
                    for window in candidate_windows:
                        # score with ml model
                        ml_score = highlight_model.score_clip(
                            proxy_path,
                            window.start_sec,
                            window.end_sec
                        )
                        
                        # combine scores: weighted average
                        final_score = (
                            config.ml_weight * ml_score +
                            config.stage1_weight * window.combined_score
                        )
                        
                        # filter by ml threshold
                        if final_score >= config.ml_threshold:
                            window.ml_score = ml_score
                            window.final_score = final_score
                            filtered_windows.append(window)
                    
                    print(f"[DETECTION] stage 2 filtered to {len(filtered_windows)} windows")
                    candidate_windows = filtered_windows
                else:
                    print(f"[DETECTION] ml model not available, using stage 1 only")
            
            # convert to segments format
            segments_with_scores = [
                (int(w.start_sec * 1000), int(w.end_sec * 1000), 
                 getattr(w, 'final_score', w.combined_score))
                for w in candidate_windows
            ]
            
            file.analysis_progress_percent = 70
            session.add(file)
            session.commit()
            
            if current_job:
                update_job_progress(current_job.id, 70)
            
            # create candidate segments with confidence scores
            publish_log('worker', 'INFO', f'💾 saving {len(segments_with_scores)} segments to database...')
            print(f"creating {len(segments_with_scores)} candidate segments in database")
            
            # determine detection method based on what was used
            if config.use_ml_stage2:
                detection_method = "motion_audio_ml"
            else:
                detection_method = "motion_audio_stage1"
            
            for start, end, confidence in segments_with_scores:
                # ensure all values are python native types (not numpy)
                seg = CandidateSegment(
                    original_file_id=file.id,
                    start_ms=int(start),
                    end_ms=int(end),
                    confidence_score=float(confidence),
                    detection_method=detection_method
                )
                session.add(seg)
            
            print(f"segments added to session, committing...")
            
            # mark as completed
            file.processing_status = "completed"
            file.analysis_progress_percent = 100
            session.add(file)
            session.commit()
            publish_log('worker', 'SUCCESS', f'🎉 analysis complete: {file.original_filename} - {len(segments_with_scores)} segments ready for sorting')
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
            
            publish_log('worker', 'INFO', f'🎬 rendering clip: {clip.filename} ({duration_sec:.1f}s)')
            print(f"rendering clip: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)
            publish_log('worker', 'SUCCESS', f'✅ clip rendered successfully')
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
            publish_log('worker', 'INFO', f'☁️  uploading to drive: {clip.filename} ({file_size_mb:.2f} MB)', {
                'filename': clip.filename,
                'size_mb': round(file_size_mb, 2),
                'year': year,
                'person': person_slug,
                'trick': trick_name
            })
            print(f"uploading clip to drive: {clip.filename} ({file_size_mb:.2f} MB)")
            print(f"  year: {year}")
            print(f"  date: {date_description}")
            print(f"  person: {person_slug}")
            print(f"  trick: {trick_name}")
            
            # upload to drive with OAuth
            drive_result = drive_service.upload_file(
                local_path=output_path,
                year=year,
                date_description=date_description,
                person_slug=person_slug,
                trick_name=trick_name,
                filename=clip.filename,
                db_session=session
            )
            
            if current_job:
                update_job_progress(current_job.id, 90)
            
            if drive_result:
                clip.drive_file_id = drive_result['drive_file_id']
                clip.drive_url = drive_result['drive_url']
                clip.is_uploaded_to_drive = True
                session.add(clip)
                session.commit()
                publish_log('worker', 'SUCCESS', f'🎉 clip uploaded to drive successfully!', {
                    'drive_file_id': drive_result['drive_file_id'][:20] + '...',
                    'filename': clip.filename
                })
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
            size_gb = file_size / (1024**3)
            publish_log('worker', 'INFO', f'📥 downloading from drive: {filename} ({size_gb:.2f} GB)', {
                'filename': filename,
                'size_gb': round(size_gb, 2)
            })
            print(f"downloading {filename} ({file_size / (1024*1024):.2f} MB) from drive...")
            if current_job:
                update_job_progress(current_job.id, 10)
            
            drive_sync.download_video_from_drive(drive_file_id, filename, dest_path)
            publish_log('worker', 'SUCCESS', f'✅ download complete: {filename}')
            
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
            
            publish_log('worker', 'SUCCESS', f'✅ video registered in database: {filename}')
            print(f"downloaded and registered: {filename}")
            
            if current_job:
                update_job_progress(current_job.id, 60)
            
            # queue analysis with extended timeout (video analysis takes time)
            from app.services.queue import enqueue_job
            enqueue_job(analyze_original_file, db_file.id, file_id=db_file.id, timeout='2h')
            publish_log('worker', 'INFO', f'📋 queued analysis job for: {filename}')
            
            if current_job:
                complete_job(current_job.id)
            
        except Exception as e:
            print(f"error downloading from drive: {e}")
            if current_job:
                fail_job(current_job.id, str(e))
            raise


def drive_sync_poller():
    """background worker that polls drive every 2 minutes"""
    import time
    from app.services.queue import enqueue_job, queue
    from app.services.log_publisher import publish_log
    
    publish_log('drive-sync', 'INFO', '🔄 Drive sync poller started')
    print("🔄 Drive sync poller started")
    
    while True:
        try:
            publish_log('drive-sync', 'INFO', '📡 Polling Drive dump folder...')
            print("📡 Polling Drive dump folder...")
            
            videos = drive_sync.get_download_queue()
            
            if videos:
                publish_log('drive-sync', 'SUCCESS', f'✅ Found {len(videos)} new videos', {
                    'count': len(videos),
                    'videos': [v['name'] for v in videos]
                })
                print(f"✅ Found {len(videos)} new videos, queuing downloads")
                
                for video in videos:
                    # check if job already queued
                    drive_file_id = video['id']
                    existing_job_queued = False
                    
                    for job in queue.jobs:
                        if job.args and len(job.args) > 0 and job.args[0] == drive_file_id:
                            print(f"  ⏭️  Job already queued for {video['name']}, skipping")
                            existing_job_queued = True
                            break
                    
                    if not existing_job_queued:
                        enqueue_job(
                            download_and_process_from_drive,
                            video['id'],
                            video['name'],
                            int(video.get('size', 0)),
                            timeout='2h'
                        )
                        publish_log('drive-sync', 'INFO', f'📥 Queued download: {video["name"]}', {
                            'filename': video['name'],
                            'size_gb': round(int(video.get('size', 0)) / (1024**3), 2)
                        })
                        print(f"  ✅ Queued: {video['name']}")
            else:
                publish_log('drive-sync', 'INFO', '📭 No new videos found')
                print("📭 No new videos found")
            
            # Publish countdown every 10 seconds
            for remaining in range(120, 0, -10):
                publish_log('drive-sync', 'DEBUG', f'⏱️  Next poll in {remaining}s', {
                    'next_poll_seconds': remaining
                })
                time.sleep(10)
                
        except Exception as e:
            publish_log('drive-sync', 'ERROR', f'⚠️  Drive sync poll error: {str(e)}')
            print(f"⚠️  Drive sync poll error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(120)


if __name__ == "__main__":
    from redis import Redis
    from rq import Worker, Queue
    
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(connection=redis_conn)
    
    print(f"Starting RQ worker, listening on queue: {queue.name}")
    worker = Worker([queue], connection=redis_conn)
    worker.work()

