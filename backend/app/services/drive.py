from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.core.config import settings
import os

class DriveService:
    def __init__(self):
        self.credentials = None
        self.service = None
        if os.path.exists(settings.GOOGLE_DRIVE_CREDENTIALS_PATH):
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_DRIVE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
    
    def _ensure_folder(self, parent_id: str, folder_name: str) -> str:
        """get or create a folder, returns folder id"""
        if not self.service:
            return None
            
        # search for existing folder
        query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            return folders[0]['id']
        
        # create folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = self.service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        return folder['id']
    
    def upload_file(self, local_path: str, year: str, session_name: str, person_slug: str, trick_name: str, filename: str) -> str:
        """
        uploads file to google drive with folder structure:
        root/year/session/person/trick/filename
        returns drive file id
        """
        if not self.service or not settings.GOOGLE_DRIVE_ROOT_FOLDER_ID:
            print("google drive not configured, skipping upload")
            return None
        
        # build folder path
        year_folder_id = self._ensure_folder(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID, year)
        session_folder_id = self._ensure_folder(year_folder_id, session_name)
        person_folder_id = self._ensure_folder(session_folder_id, person_slug)
        trick_folder_id = self._ensure_folder(person_folder_id, trick_name)
        
        # upload file
        file_metadata = {
            'name': filename,
            'parents': [trick_folder_id]
        }
        media = MediaFileUpload(local_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return file['id']
    
    def delete_file(self, file_id: str):
        """deletes a file from google drive"""
        if not self.service:
            return
        self.service.files().delete(fileId=file_id).execute()

drive_service = DriveService()

