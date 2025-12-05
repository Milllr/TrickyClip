from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from app.services.drive import drive_service
from app.core.config import settings
import os
import io
from datetime import datetime
import hashlib

class DriveSyncService:
    """handles downloading from drive dump folder and organizing processed files"""
    
    def __init__(self):
        self.dump_folder_id = settings.GOOGLE_DRIVE_DUMP_FOLDER_ID
        self.processed_folder_id = settings.GOOGLE_DRIVE_PROCESSED_FOLDER_ID
    
    def get_new_videos_from_dump(self):
        """scan drive dump folder for new videos to process"""
        if not drive_service.service or not self.dump_folder_id:
            print("drive sync not configured")
            return []
        
        # list all videos in dump folder
        query = f"'{self.dump_folder_id}' in parents and trashed=false and mimeType contains 'video/'"
        results = drive_service.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, size, createdTime)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        videos = results.get('files', [])
        print(f"found {len(videos)} videos in dump folder")
        return videos
    
    def download_video_from_drive(self, drive_file_id: str, filename: str, dest_path: str) -> str:
        """download video from drive to local VM storage"""
        print(f"downloading {filename} from drive...")
        
        request = drive_service.service.files().get_media(
            fileId=drive_file_id,
            supportsAllDrives=True
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
        if not drive_service.service:
            return
        
        # ensure processed folder exists
        if not self.processed_folder_id:
            self.processed_folder_id = drive_service._ensure_folder(
                settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
                "processed"
            )
        
        # create date subfolder
        date_str = recorded_date.strftime("%Y-%m-%d")
        date_folder_id = drive_service._ensure_folder(self.processed_folder_id, date_str)
        
        # generate clean filename: YYYY-MM-DD_original_name
        clean_name = f"{date_str}_{original_filename}"
        
        # move file
        try:
            drive_service.service.files().update(
                fileId=drive_file_id,
                addParents=date_folder_id,
                removeParents=self.dump_folder_id,
                body={'name': clean_name},
                fields='id, parents',
                supportsAllDrives=True
            ).execute()
            print(f"✅ moved to processed/{date_str}/{clean_name}")
        except Exception as e:
            print(f"⚠️ error moving file: {e}")
    
    def upload_small_clip(self, local_path: str, year: str, date_description: str, person_slug: str, trick_name: str, filename: str) -> dict:
        """upload small clip using non-resumable upload (bypasses quota issue for small files)"""
        if not drive_service.service or not settings.GOOGLE_DRIVE_ROOT_FOLDER_ID:
            print("drive not configured")
            return None
        
        file_size = os.path.getsize(local_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # build folder path
        year_folder_id = drive_service._ensure_folder(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID, year)
        date_folder_id = drive_service._ensure_folder(year_folder_id, date_description)
        person_folder_id = drive_service._ensure_folder(date_folder_id, f"{person_slug}Tricks")
        trick_folder_id = drive_service._ensure_folder(person_folder_id, trick_name)
        
        print(f"uploading clip: {filename} ({file_size_mb:.2f} MB)")
        
        # use non-resumable upload for files < 5MB, resumable for larger
        if file_size < 5 * 1024 * 1024:
            # simple upload for small files (no quota issues)
            media = MediaFileUpload(local_path, resumable=False)
        else:
            # resumable upload for larger clips
            media = MediaFileUpload(local_path, resumable=True, chunksize=1024*1024)
        
        file_metadata = {
            'name': filename,
            'parents': [trick_folder_id]
        }
        
        try:
            file = drive_service.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return {
                'drive_file_id': file['id'],
                'drive_url': file.get('webViewLink', '')
            }
        except Exception as e:
            print(f"upload error: {e}")
            raise


# singleton instance
drive_sync = DriveSyncService()

