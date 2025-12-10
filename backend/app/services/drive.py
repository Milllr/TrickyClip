from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.core.config import settings
from app.core.errors import retry_with_backoff, DriveUploadError
import os

class DriveService:
    def __init__(self):
        self.credentials = None
        self.service = None
        if os.path.exists(settings.GOOGLE_DRIVE_CREDENTIALS_PATH):
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_DRIVE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
    
    def _ensure_folder(self, parent_id: str, folder_name: str) -> str:
        """get or create a folder, returns folder id"""
        if not self.service:
            return None
            
        # search for existing folder (personal drive mode: removed supportsAllDrives)
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
    
    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def upload_file(self, local_path: str, year: str, date_description: str, person_slug: str, trick_name: str, filename: str) -> dict:
        """
        uploads file to google drive with folder structure:
        root/year/date[description]/person_tricks/trick_name/filename
        returns dict with drive_file_id and drive_url
        """
        if not self.service or not settings.GOOGLE_DRIVE_ROOT_FOLDER_ID:
            print("google drive not configured, skipping upload")
            return None
        
        # build folder path: year > date[description] > personTricks > trickName
        year_folder_id = self._ensure_folder(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID, year)
        date_folder_id = self._ensure_folder(year_folder_id, date_description)
        person_folder_id = self._ensure_folder(date_folder_id, f"{person_slug}Tricks")
        trick_folder_id = self._ensure_folder(person_folder_id, trick_name)
        
        # upload file (personal drive mode: removed supportsAllDrives)
        file_metadata = {
            'name': filename,
            'parents': [trick_folder_id]
        }
        media = MediaFileUpload(local_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return {
            'drive_file_id': file['id'],
            'drive_url': file.get('webViewLink', '')
        }

    def move_file(self, file_id: str, target_folder_id: str):
        """moves a file to a target folder (server-side move)"""
        if not self.service:
            return None
            
        file = self.service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        
        return self.service.files().update(
            fileId=file_id,
            addParents=target_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
    
    def delete_file(self, file_id: str):
        """deletes a file from google drive"""
        if not self.service:
            return
        self.service.files().delete(fileId=file_id).execute()

drive_service = DriveService()

