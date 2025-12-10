from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from app.services.drive import drive_service
from app.core.config import settings
from app.models import OriginalFile
from sqlmodel import Session, select
from app.core.db import engine
import os
import shutil
from datetime import datetime
import hashlib

class DriveSyncService:
    """handles downloading from drive dump folder and organizing processed files"""
    
    def __init__(self):
        self.dump_folder_id = settings.GOOGLE_DRIVE_DUMP_FOLDER_ID
        self.processed_folder_id = settings.GOOGLE_DRIVE_PROCESSED_FOLDER_ID
        self.min_free_space_gb = 5  # keep at least 5GB free
    
    def check_available_space(self, required_bytes: int) -> bool:
        """check if there is enough disk space for the download + buffer"""
        try:
            total, used, free = shutil.disk_usage(settings.DATA_DIR)
            # require file size + 5GB buffer
            # ensure we don't fill up the disk completely
            return free > (required_bytes + (self.min_free_space_gb * 1024 * 1024 * 1024))
        except Exception as e:
            print(f"error checking disk space: {e}")
            return False

    def get_new_videos_from_dump(self):
        """scan drive dump folder for new videos to process"""
        if not drive_service.service or not self.dump_folder_id:
            print("drive sync not configured")
            return []
        
        # list all videos in dump folder
        # personal drive: no supportsAllDrives needed
        query = f"'{self.dump_folder_id}' in parents and trashed=false and mimeType contains 'video/'"
        try:
            results = drive_service.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, size, createdTime)',
                orderBy='createdTime'  # process oldest first
            ).execute()
            
            videos = results.get('files', [])
            print(f"found {len(videos)} videos in dump folder")
            return videos
        except Exception as e:
            print(f"error listing dump folder: {e}")
            return []
    
    def get_download_queue(self) -> list:
        """
        check for new videos and return list of videos that can be downloaded now
        respecting disk space limits.
        filters out videos already in DB.
        """
        candidates = self.get_new_videos_from_dump()
        downloadable = []
        
        # get set of known drive_file_ids
        with Session(engine) as session:
            known_ids = set(session.exec(select(OriginalFile.drive_file_id)).all())
        
        # check space for each candidate
        # we check current actual free space for the first one
        # then theoretically subtract for subsequent ones in this batch
        # but realistically, the worker picks up one job at a time, so 
        # checking "can I fit THIS file right now" is sufficient.
        
        for video in candidates:
            if video['id'] in known_ids:
                continue
                
            size_bytes = int(video.get('size', 0))
            if self.check_available_space(size_bytes):
                downloadable.append(video)
                # For now, let's just return the first one that fits to avoid over-queuing
                # The periodic sync will pick up more as space clears.
                return [video] 
            else:
                print(f"skipping {video['name']} ({size_bytes/(1024**3):.2f} GB) - not enough space")
                # if we can't fit the oldest file, we probably shouldn't skip it to download a newer huge one
                # but maybe a smaller newer one? for now, let's just stop to preserve order priority.
                break 
                
        return downloadable

    def download_video_from_drive(self, drive_file_id: str, filename: str, dest_path: str) -> str:
        """download video from drive to local VM storage"""
        print(f"downloading {filename} from drive...")
        
        request = drive_service.service.files().get_media(
            fileId=drive_file_id
        )
        
        with open(dest_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"  download progress: {int(status.progress() * 100)}%")
        
        print(f"✅ downloaded to {dest_path}")
        return dest_path
    
    def move_to_processed_folder(self, drive_file_id: str, original_filename: str, recorded_date: datetime):
        """move video from dump to processed/{date}/ folder"""
        print(f"[MOVE] starting move to processed for: {original_filename} (drive_file_id: {drive_file_id})")
        
        if not drive_service.service:
            print(f"[MOVE] error: drive service not initialized")
            return
        
        # ensure processed folder exists
        if not self.processed_folder_id:
            try:
                print(f"[MOVE] creating 'processed' folder...")
                self.processed_folder_id = drive_service._ensure_folder(
                    settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
                    "processed"
                )
                print(f"[MOVE] processed folder id: {self.processed_folder_id}")
            except Exception as e:
                print(f"[MOVE] error creating processed folder: {e}")
                import traceback
                traceback.print_exc()
                return
        
        # create date subfolder
        date_str = recorded_date.strftime("%Y-%m-%d")
        print(f"[MOVE] creating date subfolder: {date_str}")
        
        try:
            date_folder_id = drive_service._ensure_folder(self.processed_folder_id, date_str)
            print(f"[MOVE] date folder id: {date_folder_id}")
        except Exception as e:
            print(f"[MOVE] error creating date folder: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # generate clean filename: YYYY-MM-DD_original_name
        clean_name = f"{date_str}_{original_filename}"
        print(f"[MOVE] new filename: {clean_name}")
        
        # move file using drive service helper (server-side move)
        try:
            # 1. Move the file
            print(f"[MOVE] moving file to folder {date_folder_id}...")
            drive_service.move_file(drive_file_id, date_folder_id)
            print(f"[MOVE] file moved successfully")
            
            # 2. Rename the file
            print(f"[MOVE] renaming file to {clean_name}...")
            drive_service.service.files().update(
                fileId=drive_file_id,
                body={'name': clean_name}
            ).execute()
            print(f"[MOVE] file renamed successfully")
            
            print(f"[MOVE] ✅ COMPLETED: moved to processed/{date_str}/{clean_name}")
        except Exception as e:
            print(f"[MOVE] ⚠️ ERROR moving file: {e}")
            import traceback
            traceback.print_exc()
    
    def upload_small_clip(self, local_path: str, year: str, date_description: str, person_slug: str, trick_name: str, filename: str) -> dict:
        """upload small clip"""
        # reuse existing upload logic from drive service
        return drive_service.upload_file(
            local_path=local_path,
            year=year,
            date_description=date_description,
            person_slug=person_slug,
            trick_name=trick_name,
            filename=filename
        )


# singleton instance
drive_sync = DriveSyncService()
